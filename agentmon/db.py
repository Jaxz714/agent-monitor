"""SQLite database operations for Agent Monitor."""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Optional

from agentmon.config import Config
from agentmon.models import UsageRecord


class Database:
    """SQLite database wrapper for usage tracking."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        db_path = self.config.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self) -> None:
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens_in INTEGER NOT NULL DEFAULT 0,
                tokens_out INTEGER NOT NULL DEFAULT 0,
                cost REAL NOT NULL DEFAULT 0.0,
                latency_ms REAL NOT NULL DEFAULT 0.0,
                success INTEGER NOT NULL DEFAULT 1,
                error_message TEXT,
                metadata TEXT
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_timestamp
            ON usage (timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_provider
            ON usage (provider, model)
        """)
        self.conn.commit()

    def insert(self, record: UsageRecord) -> int:
        """Insert a usage record and return its ID."""
        import json

        cursor = self.conn.cursor()
        ts = record.timestamp
        if ts is None:
            ts = dt.datetime.now(dt.timezone.utc)
        cursor.execute(
            """
            INSERT INTO usage
                (timestamp, provider, model, tokens_in, tokens_out, cost,
                 latency_ms, success, error_message, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts.isoformat(),
                record.provider,
                record.model,
                record.tokens_in,
                record.tokens_out,
                record.cost,
                record.latency_ms,
                1 if record.success else 0,
                record.error_message,
                json.dumps(record.metadata) if record.metadata else None,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid or 0

    def query(
        self,
        start: Optional[dt.datetime] = None,
        end: Optional[dt.datetime] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
    ) -> list[UsageRecord]:
        """Query usage records with optional filters."""
        conditions = []
        params: list = []

        if start:
            conditions.append("timestamp >= ?")
            params.append(start.isoformat())
        if end:
            conditions.append("timestamp <= ?")
            params.append(end.isoformat())
        if provider:
            conditions.append("provider = ?")
            params.append(provider)
        if model:
            conditions.append("model = ?")
            params.append(model)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
            SELECT * FROM usage
            WHERE {where}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    def aggregate(
        self,
        start: Optional[dt.datetime] = None,
        end: Optional[dt.datetime] = None,
        group_by: str = "provider",
    ) -> list[dict]:
        """Aggregate usage data grouped by provider, model, or date."""
        conditions = []
        params: list = []

        if start:
            conditions.append("timestamp >= ?")
            params.append(start.isoformat())
        if end:
            conditions.append("timestamp <= ?")
            params.append(end.isoformat())

        where = " AND ".join(conditions) if conditions else "1=1"

        if group_by == "date":
            group_expr = "date(timestamp)"
        elif group_by == "provider":
            group_expr = "provider"
        elif group_by == "model":
            group_expr = "provider, model"
        else:
            group_expr = "provider"

        sql = f"""
            SELECT
                {group_expr} as group_key,
                COUNT(*) as total_calls,
                SUM(tokens_in) as total_tokens_in,
                SUM(tokens_out) as total_tokens_out,
                SUM(cost) as total_cost,
                AVG(latency_ms) as avg_latency,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as success_rate
            FROM usage
            WHERE {where}
            GROUP BY {group_expr}
            ORDER BY total_cost DESC
        """

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_total_cost(
        self,
        start: Optional[dt.datetime] = None,
        end: Optional[dt.datetime] = None,
    ) -> float:
        """Get total cost for a time period."""
        conditions = []
        params: list = []

        if start:
            conditions.append("timestamp >= ?")
            params.append(start.isoformat())
        if end:
            conditions.append("timestamp <= ?")
            params.append(end.isoformat())

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT COALESCE(SUM(cost), 0.0) as total FROM usage WHERE {where}"

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return float(row["total"]) if row else 0.0

    def get_call_count(
        self,
        start: Optional[dt.datetime] = None,
        end: Optional[dt.datetime] = None,
    ) -> int:
        """Get total call count for a time period."""
        conditions = []
        params: list = []

        if start:
            conditions.append("timestamp >= ?")
            params.append(start.isoformat())
        if end:
            conditions.append("timestamp <= ?")
            params.append(end.isoformat())

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT COUNT(*) as cnt FROM usage WHERE {where}"

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return int(row["cnt"]) if row else 0

    def _row_to_record(self, row: sqlite3.Row) -> UsageRecord:
        """Convert a database row to a UsageRecord."""
        import json

        ts_str = row["timestamp"]
        try:
            ts = dt.datetime.fromisoformat(ts_str)
        except (ValueError, TypeError):
            ts = dt.datetime.now(dt.timezone.utc)

        metadata = None
        raw_meta = row["metadata"]
        if raw_meta:
            try:
                metadata = json.loads(raw_meta)
            except (json.JSONDecodeError, TypeError):
                metadata = None

        return UsageRecord(
            id=row["id"],
            timestamp=ts,
            provider=row["provider"],
            model=row["model"],
            tokens_in=row["tokens_in"],
            tokens_out=row["tokens_out"],
            cost=row["cost"],
            latency_ms=row["latency_ms"],
            success=bool(row["success"]),
            error_message=row["error_message"],
            metadata=metadata,
        )

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
