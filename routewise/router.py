"""Weighted gateway ranking with a native C++ engine and Python fallback."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from .config import Gateway, Settings

try:  # Native extension is optional during development and on unsupported systems.
    import routewise_cpp as _native
except ImportError:  # pragma: no cover - branch depends on local build availability
    _native = None


def native_cpp_available() -> bool:
    return _native is not None


def _normalised_weights(settings: Settings) -> tuple[float, float, float]:
    total = settings.success_weight + settings.latency_weight + settings.cost_weight
    if total <= 0:
        raise ValueError("At least one routing weight must be positive")
    return (
        settings.success_weight / total,
        settings.latency_weight / total,
        settings.cost_weight / total,
    )


def _python_rank(candidates: Iterable[Gateway], settings: Settings) -> list[dict[str, Any]]:
    success_weight, latency_weight, cost_weight = _normalised_weights(settings)
    ranked: list[dict[str, Any]] = []
    for gateway in candidates:
        if not gateway.healthy:
            continue
        latency_score = max(0.0, 1.0 - gateway.latency_ms / settings.latency_reference_ms)
        cost_score = max(0.0, 1.0 - gateway.cost_units / settings.cost_reference_units)
        score = (
            success_weight * gateway.success_rate
            + latency_weight * latency_score
            + cost_weight * cost_score
        )
        ranked.append({
            "gateway_id": gateway.gateway_id,
            "name": gateway.name,
            "score": score,
            "success_rate": gateway.success_rate,
            "latency_ms": gateway.latency_ms,
            "cost_units": gateway.cost_units,
        })
    # Rank using full precision, then round only for the public-facing score.
    ranked.sort(key=lambda item: (-item["score"], item["gateway_id"]))
    for item in ranked:
        item["score"] = round(item["score"], 6)
    return ranked


def rank_gateways(candidates: Iterable[Gateway], settings: Settings) -> list[dict[str, Any]]:
    """Rank healthy gateways using weighted success, latency, and cost signals."""
    candidate_list = list(candidates)
    if _native is None:
        return _python_rank(candidate_list, settings)
    rows = [asdict(gateway) for gateway in candidate_list]
    result = _native.rank_gateways(
        rows,
        settings.success_weight,
        settings.latency_weight,
        settings.cost_weight,
        settings.latency_reference_ms,
        settings.cost_reference_units,
    )
    return list(result)
