"""Data models for Agent Monitor."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UsageRecord:
    """A single API call usage record."""

    id: Optional[int] = None
    timestamp: Optional[dt.datetime] = None
    provider: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[dict] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = dt.datetime.now(dt.timezone.utc)


@dataclass
class BudgetConfig:
    """Budget configuration."""

    monthly_limit: Optional[float] = None
    warn_threshold: float = 0.8  # 80%


@dataclass
class CostSummary:
    """Aggregated cost summary."""

    period: str = ""
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None
    total_cost: float = 0.0
    total_calls: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    avg_latency_ms: float = 0.0
    success_rate: float = 0.0
    by_provider: dict = field(default_factory=dict)
    by_model: dict = field(default_factory=dict)


@dataclass
class ProviderComparison:
    """Provider cost comparison entry."""

    provider: str = ""
    model: str = ""
    total_cost: float = 0.0
    total_calls: int = 0
    avg_cost_per_call: float = 0.0
    total_tokens: int = 0
    cost_per_1k_tokens: float = 0.0
