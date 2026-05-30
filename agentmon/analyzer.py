"""Cost analysis and reporting for Agent Monitor."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from agentmon.config import Config
from agentmon.db import Database
from agentmon.models import CostSummary, ProviderComparison


class Analyzer:
    """Analyze usage data and generate reports."""

    def __init__(self, db: Database, config: Optional[Config] = None) -> None:
        self.db = db
        self.config = config or Config()

    def _period_bounds(
        self, period: str
    ) -> tuple[dt.datetime, dt.datetime]:
        """Get start and end datetimes for a period."""
        now = dt.datetime.now(dt.timezone.utc)
        today = now.date()

        if period == "day":
            start = dt.datetime.combine(today, dt.time.min, tzinfo=dt.timezone.utc)
            end = now
        elif period == "week":
            start_of_week = today - dt.timedelta(days=today.weekday())
            start = dt.datetime.combine(
                start_of_week, dt.time.min, tzinfo=dt.timezone.utc
            )
            end = now
        elif period == "month":
            start_of_month = today.replace(day=1)
            start = dt.datetime.combine(
                start_of_month, dt.time.min, tzinfo=dt.timezone.utc
            )
            end = now
        elif period == "year":
            start_of_year = today.replace(month=1, day=1)
            start = dt.datetime.combine(
                start_of_year, dt.time.min, tzinfo=dt.timezone.utc
            )
            end = now
        else:
            # Default to month
            start_of_month = today.replace(day=1)
            start = dt.datetime.combine(
                start_of_month, dt.time.min, tzinfo=dt.timezone.utc
            )
            end = now

        return start, end

    def dashboard(self, period: str = "month") -> CostSummary:
        """Generate a cost dashboard for the given period."""
        start, end = self._period_bounds(period)
        return self._build_summary(period, start, end)

    def custom_report(
        self, start: dt.datetime, end: dt.datetime
    ) -> CostSummary:
        """Generate a report for a custom date range."""
        return self._build_summary("custom", start, end)

    def _build_summary(
        self, period: str, start: dt.datetime, end: dt.datetime
    ) -> CostSummary:
        """Build a CostSummary from database data."""
        total_cost = self.db.get_total_cost(start, end)
        total_calls = self.db.get_call_count(start, end)

        by_provider_raw = self.db.aggregate(start, end, group_by="provider")
        by_model_raw = self.db.aggregate(start, end, group_by="model")

        total_tokens_in = 0
        total_tokens_out = 0
        weighted_latency = 0.0
        total_success = 0

        by_provider = {}
        for row in by_provider_raw:
            total_tokens_in += row["total_tokens_in"] or 0
            total_tokens_out += row["total_tokens_out"] or 0
            weighted_latency += (row["avg_latency"] or 0) * (row["total_calls"] or 0)
            total_success += int((row["success_rate"] or 0) * (row["total_calls"] or 0))
            by_provider[row["group_key"]] = {
                "cost": row["total_cost"] or 0.0,
                "calls": row["total_calls"] or 0,
                "tokens_in": row["total_tokens_in"] or 0,
                "tokens_out": row["total_tokens_out"] or 0,
                "avg_latency": row["avg_latency"] or 0.0,
                "success_rate": row["success_rate"] or 0.0,
            }

        by_model = {}
        for row in by_model_raw:
            key = row["group_key"] or "unknown"
            by_model[key] = {
                "cost": row["total_cost"] or 0.0,
                "calls": row["total_calls"] or 0,
                "tokens_in": row["total_tokens_in"] or 0,
                "tokens_out": row["total_tokens_out"] or 0,
            }

        avg_latency = (weighted_latency / total_calls) if total_calls > 0 else 0.0
        success_rate = (total_success / total_calls) if total_calls > 0 else 0.0

        return CostSummary(
            period=period,
            start_date=start.date(),
            end_date=end.date(),
            total_cost=round(total_cost, 4),
            total_calls=total_calls,
            total_tokens_in=total_tokens_in,
            total_tokens_out=total_tokens_out,
            avg_latency_ms=round(avg_latency, 2),
            success_rate=round(success_rate, 4),
            by_provider=by_provider,
            by_model=by_model,
        )

    def provider_comparison(
        self, period: str = "month"
    ) -> list[ProviderComparison]:
        """Compare costs across providers and models."""
        start, end = self._period_bounds(period)
        rows = self.db.aggregate(start, end, group_by="model")

        comparisons = []
        for row in rows:
            total_tokens = (row["total_tokens_in"] or 0) + (row["total_tokens_out"] or 0)
            total_cost = row["total_cost"] or 0.0
            total_calls = row["total_calls"] or 0

            # Parse provider from group_key (format: "provider, model" or just "provider")
            group_key = row["group_key"] or ""
            parts = group_key.split(", ")
            if len(parts) == 2:
                provider, model = parts[0], parts[1]
            else:
                provider, model = group_key, ""

            comparisons.append(
                ProviderComparison(
                    provider=provider,
                    model=model,
                    total_cost=round(total_cost, 4),
                    total_calls=total_calls,
                    avg_cost_per_call=round(total_cost / total_calls, 6)
                    if total_calls > 0
                    else 0.0,
                    total_tokens=total_tokens,
                    cost_per_1k_tokens=round(
                        (total_cost / total_tokens * 1000), 6
                    )
                    if total_tokens > 0
                    else 0.0,
                )
            )

        comparisons.sort(key=lambda c: c.total_cost, reverse=True)
        return comparisons

    def get_recent_calls(self, limit: int = 20) -> list:
        """Get the most recent API calls."""
        return self.db.query(limit=limit)
