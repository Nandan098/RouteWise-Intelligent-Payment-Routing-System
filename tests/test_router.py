from __future__ import annotations

from routewise.config import Gateway, Settings
from routewise.router import _python_rank, rank_gateways


def settings() -> Settings:
    return Settings(
        database_path="unused.db",
        gateway_config_path="unused.json",
        success_weight=0.70,
        latency_weight=0.20,
        cost_weight=0.10,
        latency_reference_ms=500,
        cost_reference_units=0.05,
    )


def gateways() -> list[Gateway]:
    return [
        Gateway("a", "A", 0.98, 150, 0.02, True),
        Gateway("b", "B", 0.95, 100, 0.025, True),
        Gateway("disabled", "Disabled", 1.0, 50, 0.0, False),
    ]


def test_python_weighted_rank_chooses_expected_candidate():
    ranked = _python_rank(gateways(), settings())
    assert ranked[0]["gateway_id"] == "a"
    assert [row["gateway_id"] for row in ranked] == ["a", "b"]


def test_public_router_matches_fallback_order():
    assert [row["gateway_id"] for row in rank_gateways(gateways(), settings())] == ["a", "b"]


def test_invalid_weights_are_rejected():
    invalid = Settings("db", "gateways", success_weight=0, latency_weight=0, cost_weight=0)
    try:
        _python_rank(gateways(), invalid)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("Expected invalid weights to raise ValueError")
