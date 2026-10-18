"""Business logic for selecting payment gateways and recording outcomes."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from .adaptive import rank_ucb
from .config import Gateway, Settings, load_gateways
from .database import Database
from .router import native_cpp_available, rank_gateways
from .schemas import FeedbackRequest, RouteRequest

logger = logging.getLogger(__name__)


class IdempotencyConflict(Exception):
    """A transaction ID was reused with a different request/feedback payload."""


class NoHealthyGateway(Exception):
    """There is no eligible simulated gateway."""


class RouteNotFound(Exception):
    """Feedback was submitted for a transaction that has not been routed."""


class FeedbackConflict(Exception):
    """The route already has feedback with a different outcome."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class RoutingService:
    def __init__(self, database: Database, settings: Settings):
        self.database = database
        self.settings = settings
        self.gateways, routing_config = load_gateways(settings.gateway_config_path)
        # JSON provides sensible project defaults; explicit environment variables win.
        env_to_field = {
            "ROUTEWISE_SUCCESS_WEIGHT": "success_weight",
            "ROUTEWISE_LATENCY_WEIGHT": "latency_weight",
            "ROUTEWISE_COST_WEIGHT": "cost_weight",
            "ROUTEWISE_LATENCY_REFERENCE_MS": "latency_reference_ms",
            "ROUTEWISE_COST_REFERENCE_UNITS": "cost_reference_units",
        }
        updates: dict[str, Any] = {}
        for field_name in (
            "success_weight", "latency_weight", "cost_weight",
            "latency_reference_ms", "cost_reference_units",
        ):
            env_name = next(key for key, value in env_to_field.items() if value == field_name)
            if os.getenv(env_name) is None and field_name in routing_config:
                updates[field_name] = float(routing_config[field_name])
        if updates:
            self.settings = replace(settings, **updates)
        self.settings.validate()
        self._gateway_by_id = {gateway.gateway_id: gateway for gateway in self.gateways}

    def route(self, request: RouteRequest) -> dict[str, Any]:
        payload = json.dumps(request.canonical_payload(), sort_keys=True, separators=(",", ":"))
        with self.database.transaction() as connection:
            previous = connection.execute(
                "SELECT * FROM routes WHERE transaction_id = ?", (request.transaction_id,)
            ).fetchone()
            if previous:
                if previous["request_json"] != payload:
                    raise IdempotencyConflict(
                        "transaction_id already exists with a different request payload"
                    )
                result = self.database.route_to_dict(previous)
                result["idempotent_replay"] = True
                return result

            if request.policy.value == "weighted":
                ranked = rank_gateways(self.gateways, self.settings)
                if not ranked:
                    raise NoHealthyGateway("No healthy payment gateway is currently available")
                selected = ranked[0]
                routing_score = float(selected["score"])
                reasons = [
                    f"Highest weighted score ({routing_score:.4f}) among healthy gateways.",
                    f"Configured baseline: {selected['success_rate']:.1%} success, "
                    f"{selected['latency_ms']:.0f} ms latency, "
                    f"{selected['cost_units']:.4f} cost units.",
                ]
            else:
                feedback_stats = self.database.feedback_stats(connection)
                ranked = rank_ucb(self.gateways, feedback_stats)
                if not ranked:
                    raise NoHealthyGateway("No healthy payment gateway is currently available")
                selected = ranked[0]
                routing_score = float(selected["score"])
                reasons = list(selected.get("reasons", []))

            gateway = self._gateway_by_id[selected["gateway_id"]]
            created_at = _utc_now()
            connection.execute(
                """INSERT INTO routes (
                    transaction_id, request_json, amount, currency, policy,
                    gateway_id, gateway_name, routing_score, expected_success_rate,
                    expected_latency_ms, estimated_cost_units, reasons_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request.transaction_id, payload, float(request.amount), request.currency,
                    request.policy.value, gateway.gateway_id, gateway.name, routing_score,
                    float(selected["success_rate"]), float(selected["latency_ms"]),
                    float(selected["cost_units"]), json.dumps(reasons), created_at,
                ),
            )
            return {
                "transaction_id": request.transaction_id,
                "gateway_id": gateway.gateway_id,
                "gateway_name": gateway.name,
                "policy": request.policy.value,
                "routing_score": routing_score,
                "expected_success_rate": float(selected["success_rate"]),
                "expected_latency_ms": float(selected["latency_ms"]),
                "estimated_cost_units": float(selected["cost_units"]),
                "reasons": reasons,
                "created_at": created_at,
                "idempotent_replay": False,
            }

    def record_feedback(self, request: FeedbackRequest) -> dict[str, Any]:
        with self.database.transaction() as connection:
            route = connection.execute(
                "SELECT gateway_id FROM routes WHERE transaction_id = ?",
                (request.transaction_id,),
            ).fetchone()
            if route is None:
                raise RouteNotFound("Route the transaction before submitting feedback")
            previous = connection.execute(
                "SELECT * FROM feedback WHERE transaction_id = ?", (request.transaction_id,)
            ).fetchone()
            if previous:
                same = (
                    bool(previous["success"]) == request.success
                    and abs(float(previous["actual_latency_ms"]) - request.actual_latency_ms) < 1e-9
                )
                if not same:
                    raise FeedbackConflict("Feedback already exists with a different outcome")
                return {
                    "transaction_id": request.transaction_id,
                    "gateway_id": previous["gateway_id"],
                    "success": bool(previous["success"]),
                    "actual_latency_ms": float(previous["actual_latency_ms"]),
                    "recorded_at": previous["recorded_at"],
                    "idempotent_replay": True,
                }
            recorded_at = _utc_now()
            connection.execute(
                "INSERT INTO feedback (transaction_id, gateway_id, success, actual_latency_ms, recorded_at) VALUES (?, ?, ?, ?, ?)",
                (request.transaction_id, route["gateway_id"], int(request.success), request.actual_latency_ms, recorded_at),
            )
            return {
                "transaction_id": request.transaction_id,
                "gateway_id": route["gateway_id"],
                "success": request.success,
                "actual_latency_ms": float(request.actual_latency_ms),
                "recorded_at": recorded_at,
                "idempotent_replay": False,
            }

    def get_route(self, transaction_id: str) -> dict[str, Any] | None:
        return self.database.get_route(transaction_id)

    def list_routes(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.database.list_routes(limit)

    def get_gateways(self) -> list[dict[str, Any]]:
        stats = self.database.get_feedback_stats()
        output: list[dict[str, Any]] = []
        for gateway in self.gateways:
            observed = stats.get(gateway.gateway_id)
            output.append({
                "gateway_id": gateway.gateway_id,
                "name": gateway.name,
                "base_success_rate": gateway.success_rate,
                "base_latency_ms": gateway.latency_ms,
                "cost_units": gateway.cost_units,
                "healthy": gateway.healthy,
                "feedback_count": int(observed["sample_count"]) if observed else 0,
                "observed_success_rate": float(observed["success_rate"]) if observed else None,
                "observed_average_latency_ms": float(observed["avg_latency_ms"]) if observed else None,
            })
        return output

    def get_stats(self) -> dict[str, Any]:
        return self.database.get_stats()

    @staticmethod
    def native_cpp_available() -> bool:
        return native_cpp_available()
