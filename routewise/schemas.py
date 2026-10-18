"""Pydantic request and response contracts for the RouteWise API."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoutingPolicy(str, Enum):
    WEIGHTED = "weighted"
    UCB = "ucb"


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    amount: float = Field(gt=0, le=1_000_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    policy: RoutingPolicy = RoutingPolicy.WEIGHTED
    timestamp: datetime | None = None

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        value = value.upper()
        if not value.isalpha():
            raise ValueError("Currency must contain three alphabetic letters")
        return value

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "amount": float(self.amount),
            "currency": self.currency,
            "policy": self.policy.value,
            "timestamp": self.timestamp.isoformat(timespec="microseconds") if self.timestamp else None,
        }


class RouteResponse(BaseModel):
    transaction_id: str
    gateway_id: str
    gateway_name: str
    policy: RoutingPolicy
    routing_score: float | None = None
    expected_success_rate: float
    expected_latency_ms: float
    estimated_cost_units: float
    reasons: list[str]
    created_at: str
    idempotent_replay: bool = False


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1, max_length=128)
    success: bool
    actual_latency_ms: float = Field(gt=0, le=600_000)


class FeedbackResponse(BaseModel):
    transaction_id: str
    gateway_id: str
    success: bool
    actual_latency_ms: float
    recorded_at: str
    idempotent_replay: bool = False


class HealthResponse(BaseModel):
    status: str
    native_cpp_available: bool
    database: str


class GatewayResponse(BaseModel):
    gateway_id: str
    name: str
    base_success_rate: float
    base_latency_ms: float
    cost_units: float
    healthy: bool
    feedback_count: int = 0
    observed_success_rate: float | None = None
    observed_average_latency_ms: float | None = None


class StatsResponse(BaseModel):
    total_routes: int
    routes_by_gateway: dict[str, int]
    total_feedback: int
    observed_success_rate: float | None
    average_actual_latency_ms: float | None


class ErrorResponse(BaseModel):
    detail: str
