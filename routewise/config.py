"""Application configuration loaded from environment variables and JSON."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_path: Path
    gateway_config_path: Path
    default_currency: str = "INR"
    success_weight: float = 0.70
    latency_weight: float = 0.20
    cost_weight: float = 0.10
    latency_reference_ms: float = 500.0
    cost_reference_units: float = 0.05
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(
        cls,
        database_path: str | Path | None = None,
        gateway_config_path: str | Path | None = None,
    ) -> "Settings":
        """Create settings; explicit arguments take precedence over environment."""
        db_value = database_path or os.getenv("ROUTEWISE_DATABASE_PATH")
        gateway_value = gateway_config_path or os.getenv("ROUTEWISE_GATEWAY_CONFIG")
        return cls(
            database_path=Path(db_value) if db_value else PROJECT_ROOT / "data" / "routewise.db",
            gateway_config_path=Path(gateway_value) if gateway_value else PROJECT_ROOT / "config" / "gateways.json",
            default_currency=os.getenv("ROUTEWISE_DEFAULT_CURRENCY", "INR").upper(),
            success_weight=float(os.getenv("ROUTEWISE_SUCCESS_WEIGHT", "0.70")),
            latency_weight=float(os.getenv("ROUTEWISE_LATENCY_WEIGHT", "0.20")),
            cost_weight=float(os.getenv("ROUTEWISE_COST_WEIGHT", "0.10")),
            latency_reference_ms=float(os.getenv("ROUTEWISE_LATENCY_REFERENCE_MS", "500")),
            cost_reference_units=float(os.getenv("ROUTEWISE_COST_REFERENCE_UNITS", "0.05")),
            host=os.getenv("ROUTEWISE_HOST", "127.0.0.1"),
            port=int(os.getenv("ROUTEWISE_PORT", "8000")),
        )

    def validate(self) -> None:
        weights = (self.success_weight, self.latency_weight, self.cost_weight)
        if any(weight < 0 for weight in weights):
            raise ValueError("Routing weights cannot be negative")
        if sum(weights) <= 0:
            raise ValueError("At least one routing weight must be positive")
        if self.latency_reference_ms <= 0 or self.cost_reference_units <= 0:
            raise ValueError("Latency and cost reference values must be positive")
        if len(self.default_currency) != 3:
            raise ValueError("Default currency must be a three-letter code")


@dataclass(frozen=True)
class Gateway:
    gateway_id: str
    name: str
    success_rate: float
    latency_ms: float
    cost_units: float
    healthy: bool = True


def load_gateways(path: str | Path) -> tuple[list[Gateway], dict[str, Any]]:
    """Read gateway candidates and optional routing configuration from JSON."""
    gateway_path = Path(path)
    if not gateway_path.exists():
        raise FileNotFoundError(f"Gateway configuration not found: {gateway_path}")
    payload = json.loads(gateway_path.read_text(encoding="utf-8"))
    gateways = [
        Gateway(
            gateway_id=str(item["gateway_id"]),
            name=str(item["name"]),
            success_rate=float(item["success_rate"]),
            latency_ms=float(item["latency_ms"]),
            cost_units=float(item["cost_units"]),
            healthy=bool(item.get("healthy", True)),
        )
        for item in payload.get("gateways", [])
    ]
    if not gateways:
        raise ValueError("Gateway configuration must contain at least one gateway")
    ids = [gateway.gateway_id for gateway in gateways]
    if len(ids) != len(set(ids)):
        raise ValueError("Gateway identifiers must be unique")
    for gateway in gateways:
        if not gateway.gateway_id.strip() or not gateway.name.strip():
            raise ValueError("Gateway IDs and names cannot be empty")
        if not 0 <= gateway.success_rate <= 1:
            raise ValueError(f"Invalid success rate for {gateway.gateway_id}")
        if gateway.latency_ms <= 0 or gateway.cost_units < 0:
            raise ValueError(f"Invalid latency/cost for {gateway.gateway_id}")
    routing = payload.get("routing", {})
    return gateways, routing
