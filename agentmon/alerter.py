"""Budget alerts for Agent Monitor."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from agentmon.config import Config
from agentmon.db import Database


class BudgetAlerter:
    """Monitor budget usage and generate alerts."""

    def __init__(self, db: Database, config: Optional[Config] = None) -> None:
        self.db = db
        self.config = config or Config()

    def get_monthly_spend(self) -> float:
        """Get current month's total spend."""
        now = dt.datetime.now(dt.timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.db.get_total_cost(start=start_of_month, end=now)

    def get_budget_status(self) -> dict:
        """Get the current budget status.

        Returns:
            Dict with: budget, spent, remaining, percentage_used, is_over, is_warning
        """
        budget = self.config.monthly_budget
        if budget is None:
            return {
                "budget": None,
                "spent": self.get_monthly_spend(),
                "remaining": None,
                "percentage_used": 0.0,
                "is_over": False,
                "is_warning": False,
                "message": "No monthly budget set. Use 'agentmon budget set <amount>' to set one.",
            }

        spent = self.get_monthly_spend()
        remaining = max(budget - spent, 0.0)
        pct = (spent / budget) * 100 if budget > 0 else 0.0
        is_over = spent >= budget
        is_warning = pct >= (self.config.warn_threshold * 100)

        if is_over:
            message = f"OVER BUDGET! Spent ${spent:.2f} of ${budget:.2f} budget (${spent - budget:.2f} over)."
        elif is_warning:
            message = f"WARNING: {pct:.1f}% of monthly budget used (${spent:.2f} / ${budget:.2f})."
        else:
            message = f"Budget OK: ${spent:.2f} of ${budget:.2f} used ({pct:.1f}%)."

        return {
            "budget": budget,
            "spent": round(spent, 4),
            "remaining": round(remaining, 4),
            "percentage_used": round(pct, 2),
            "is_over": is_over,
            "is_warning": is_warning,
            "message": message,
        }

    def set_budget(self, amount: float) -> None:
        """Set the monthly budget."""
        self.config.monthly_budget = amount

    def check_alerts(self) -> list[str]:
        """Check for any active alerts and return warning messages."""
        alerts = []
        status = self.get_budget_status()

        if status["is_over"]:
            alerts.append(
                f"CRITICAL: Monthly budget exceeded! "
                f"Spent ${status['spent']:.2f} of ${status['budget']:.2f} "
                f"(${status['spent'] - status['budget']:.2f} over)."
            )
        elif status["is_warning"]:
            alerts.append(
                f"WARNING: Approaching monthly budget limit. "
                f"Used {status['percentage_used']:.1f}% "
                f"(${status['spent']:.2f} / ${status['budget']:.2f})."
            )

        return alerts
