"""Usage tracking - decorator and context manager for API calls."""

from __future__ import annotations

import functools
import time
import traceback
from typing import Any, Callable, Optional, TypeVar

from agentmon.config import Config
from agentmon.db import Database
from agentmon.models import UsageRecord

F = TypeVar("F", bound=Callable[..., Any])


class ActiveTracking:
    """Represents an active tracking context for a single API call."""

    def __init__(self, provider: str, model: str, db: Database, config: Config) -> None:
        self.provider = provider
        self.model = model
        self.db = db
        self.config = config
        self.tokens_in: int = 0
        self.tokens_out: int = 0
        self.cost: Optional[float] = None
        self.success: bool = True
        self.error_message: Optional[str] = None
        self.metadata: dict = {}
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._recorded: bool = False

    def record(
        self,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        **metadata: Any,
    ) -> None:
        """Record usage data for this tracking session."""
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        if cost is not None:
            self.cost = cost
        self.success = success
        self.error_message = error_message
        if metadata:
            self.metadata.update(metadata)

    def _save(self) -> None:
        """Persist the record to the database."""
        if self._recorded:
            return
        self._recorded = True

        latency_ms = (self._end_time - self._start_time) * 1000

        # Auto-calculate cost if not explicitly set
        if self.cost is None:
            self.cost = self.config.calculate_cost(
                self.provider, self.model, self.tokens_in, self.tokens_out
            )

        record = UsageRecord(
            provider=self.provider,
            model=self.model,
            tokens_in=self.tokens_in,
            tokens_out=self.tokens_out,
            cost=self.cost,
            latency_ms=round(latency_ms, 2),
            success=self.success,
            error_message=self.error_message,
            metadata=self.metadata if self.metadata else None,
        )
        self.db.insert(record)


class UsageTracker:
    """Main tracker class providing context manager and decorator interfaces."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        self.db = Database(self.config)

    def track(
        self,
        provider: str = "",
        model: str = "",
        auto_cost: bool = True,
    ) -> _TrackingContext:
        """Create a tracking context manager.

        Args:
            provider: The API provider name (e.g. "anthropic", "openai")
            model: The model name (e.g. "claude-sonnet-4-20250514")
            auto_cost: Whether to auto-calculate cost from pricing data

        Returns:
            A context manager that tracks usage.
        """
        return _TrackingContext(self, provider, model)

    def close(self) -> None:
        """Close the tracker and its database connection."""
        self.db.close()


class _TrackingContext:
    """Context manager for tracking a single API call."""

    def __init__(
        self, tracker: UsageTracker, provider: str, model: str
    ) -> None:
        self.tracker = tracker
        self.provider = provider
        self.model = model
        self._active: Optional[ActiveTracking] = None

    def __enter__(self) -> ActiveTracking:
        self._active = ActiveTracking(
            self.provider,
            self.model,
            self.tracker.db,
            self.tracker.config,
        )
        self._active._start_time = time.perf_counter()
        return self._active

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> None:
        if self._active is not None:
            self._active._end_time = time.perf_counter()
            if exc_type is not None:
                self._active.success = False
                self._active.error_message = str(exc_val)
            self._active._save()


def track(
    provider: str = "",
    model: str = "",
) -> Callable[[F], F]:
    """Decorator to automatically track API call usage.

    The decorated function must return a tuple of (response, tokens_in, tokens_out)
    OR return any value and use the `record` method on the injected tracker.

    For simpler use, the decorated function can return a dict/obj with:
      - usage.input_tokens / usage.output_tokens
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracker = UsageTracker()
            try:
                with tracker.track(provider, model) as t:
                    result = func(*args, **kwargs)

                    # Auto-extract tokens from common response shapes
                    if hasattr(result, "usage"):
                        usage = result.usage
                        tokens_in = getattr(usage, "input_tokens", 0) or getattr(
                            usage, "prompt_tokens", 0
                        )
                        tokens_out = getattr(usage, "output_tokens", 0) or getattr(
                            usage, "completion_tokens", 0
                        )
                        t.record(tokens_in=tokens_in, tokens_out=tokens_out)
                    elif isinstance(result, dict) and "usage" in result:
                        usage = result["usage"]
                        tokens_in = usage.get("input_tokens", usage.get("prompt_tokens", 0))
                        tokens_out = usage.get("output_tokens", usage.get("completion_tokens", 0))
                        t.record(tokens_in=tokens_in, tokens_out=tokens_out)

                    return result
            finally:
                tracker.close()

        return wrapper  # type: ignore

    return decorator
