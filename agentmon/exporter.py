"""CSV/JSON export for Agent Monitor."""

from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Optional

from agentmon.config import Config
from agentmon.db import Database
from agentmon.models import UsageRecord


class Exporter:
    """Export usage data to CSV or JSON."""

    def __init__(self, db: Database, config: Optional[Config] = None) -> None:
        self.db = db
        self.config = config or Config()

    def export(
        self,
        format: str = "csv",
        start: Optional[dt.datetime] = None,
        end: Optional[dt.datetime] = None,
        provider: Optional[str] = None,
        output_path: Optional[Path] = None,
        limit: int = 10000,
    ) -> Path:
        """Export usage data.

        Args:
            format: "csv" or "json"
            start: Start datetime filter
            end: End datetime filter
            provider: Provider filter
            output_path: Custom output path (default: auto-generated in export dir)
            limit: Max records to export

        Returns:
            Path to the exported file.
        """
        records = self.db.query(
            start=start, end=end, provider=provider, limit=limit
        )

        if output_path is None:
            export_dir = self.config.export_dir
            export_dir.mkdir(parents=True, exist_ok=True)
            timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = export_dir / f"usage_export_{timestamp}.{format}"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "csv":
            self._export_csv(records, output_path)
        elif format == "json":
            self._export_json(records, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'csv' or 'json'.")

        return output_path

    def _export_csv(self, records: list[UsageRecord], path: Path) -> None:
        """Export records to CSV."""
        fieldnames = [
            "id",
            "timestamp",
            "provider",
            "model",
            "tokens_in",
            "tokens_out",
            "cost",
            "latency_ms",
            "success",
            "error_message",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        "id": record.id,
                        "timestamp": record.timestamp.isoformat()
                        if record.timestamp
                        else "",
                        "provider": record.provider,
                        "model": record.model,
                        "tokens_in": record.tokens_in,
                        "tokens_out": record.tokens_out,
                        "cost": f"{record.cost:.6f}",
                        "latency_ms": f"{record.latency_ms:.2f}",
                        "success": record.success,
                        "error_message": record.error_message or "",
                    }
                )

    def _export_json(self, records: list[UsageRecord], path: Path) -> None:
        """Export records to JSON."""
        data = []
        for record in records:
            data.append(
                {
                    "id": record.id,
                    "timestamp": record.timestamp.isoformat()
                    if record.timestamp
                    else None,
                    "provider": record.provider,
                    "model": record.model,
                    "tokens_in": record.tokens_in,
                    "tokens_out": record.tokens_out,
                    "cost": round(record.cost, 6),
                    "latency_ms": round(record.latency_ms, 2),
                    "success": record.success,
                    "error_message": record.error_message,
                    "metadata": record.metadata,
                }
            )

        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"exported_at": dt.datetime.now(dt.timezone.utc).isoformat(), "records": data},
                f,
                indent=2,
            )
