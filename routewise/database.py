"""Small SQLite persistence layer with explicit transactions."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.path), timeout=10.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS routes (
                    transaction_id TEXT PRIMARY KEY,
                    request_json TEXT NOT NULL,
                    amount REAL NOT NULL CHECK(amount > 0),
                    currency TEXT NOT NULL CHECK(length(currency) = 3),
                    policy TEXT NOT NULL CHECK(policy IN ('weighted', 'ucb')),
                    gateway_id TEXT NOT NULL,
                    gateway_name TEXT NOT NULL,
                    routing_score REAL,
                    expected_success_rate REAL NOT NULL,
                    expected_latency_ms REAL NOT NULL,
                    estimated_cost_units REAL NOT NULL,
                    reasons_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_routes_created_at ON routes(created_at);
                CREATE INDEX IF NOT EXISTS idx_routes_gateway_id ON routes(gateway_id);
                CREATE TABLE IF NOT EXISTS feedback (
                    transaction_id TEXT PRIMARY KEY,
                    gateway_id TEXT NOT NULL,
                    success INTEGER NOT NULL CHECK(success IN (0, 1)),
                    actual_latency_ms REAL NOT NULL CHECK(actual_latency_ms > 0),
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY(transaction_id) REFERENCES routes(transaction_id)
                );
                CREATE INDEX IF NOT EXISTS idx_feedback_gateway_id ON feedback(gateway_id);
                """
            )
        finally:
            connection.close()

    @contextmanager
    def transaction(self, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def route_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "transaction_id": row["transaction_id"],
            "gateway_id": row["gateway_id"],
            "gateway_name": row["gateway_name"],
            "policy": row["policy"],
            "routing_score": row["routing_score"],
            "expected_success_rate": row["expected_success_rate"],
            "expected_latency_ms": row["expected_latency_ms"],
            "estimated_cost_units": row["estimated_cost_units"],
            "reasons": json.loads(row["reasons_json"]),
            "created_at": row["created_at"],
            "idempotent_replay": False,
        }

    def get_route(self, transaction_id: str) -> dict[str, Any] | None:
        with self.transaction(immediate=False) as connection:
            row = connection.execute(
                "SELECT * FROM routes WHERE transaction_id = ?", (transaction_id,)
            ).fetchone()
            return self.route_to_dict(row) if row else None

    def list_routes(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.transaction(immediate=False) as connection:
            rows = connection.execute(
                "SELECT * FROM routes ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [self.route_to_dict(row) for row in rows]

    @staticmethod
    def feedback_stats(connection: sqlite3.Connection) -> dict[str, dict[str, float | int]]:
        rows = connection.execute(
            """SELECT gateway_id, COUNT(*) AS sample_count,
                      SUM(success) AS success_count,
                      AVG(actual_latency_ms) AS avg_latency_ms
               FROM feedback GROUP BY gateway_id"""
        ).fetchall()
        return {
            row["gateway_id"]: {
                "sample_count": int(row["sample_count"]),
                "success_count": int(row["success_count"] or 0),
                "success_rate": float(row["success_count"] or 0) / int(row["sample_count"]),
                "avg_latency_ms": float(row["avg_latency_ms"]),
            }
            for row in rows
        }

    def get_feedback_stats(self) -> dict[str, dict[str, float | int]]:
        with self.transaction(immediate=False) as connection:
            return self.feedback_stats(connection)

    def get_stats(self) -> dict[str, Any]:
        with self.transaction(immediate=False) as connection:
            total_routes = int(connection.execute("SELECT COUNT(*) FROM routes").fetchone()[0])
            gateway_rows = connection.execute(
                "SELECT gateway_id, COUNT(*) AS total FROM routes GROUP BY gateway_id"
            ).fetchall()
            feedback_row = connection.execute(
                "SELECT COUNT(*) AS total, AVG(success) AS success_rate, AVG(actual_latency_ms) AS latency FROM feedback"
            ).fetchone()
            return {
                "total_routes": total_routes,
                "routes_by_gateway": {row["gateway_id"]: int(row["total"]) for row in gateway_rows},
                "total_feedback": int(feedback_row["total"]),
                "observed_success_rate": float(feedback_row["success_rate"]) if feedback_row["success_rate"] is not None else None,
                "average_actual_latency_ms": float(feedback_row["latency"]) if feedback_row["latency"] is not None else None,
            }
