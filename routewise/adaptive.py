"""UCB1 adaptive gateway selection based on recorded simulated feedback."""
from __future__ import annotations

import math
from typing import Any, Iterable

from .config import Gateway


def rank_ucb(
    gateways: Iterable[Gateway],
    feedback_stats: dict[str, dict[str, float | int]],
) -> list[dict[str, Any]]:
    """Rank healthy gateways using UCB1; untried gateways are explored first.

    The reward is transaction success (1 for success, 0 for failure). UCB is
    an educational bandit policy and is not a calibrated production risk model.
    """
    candidates = [gateway for gateway in gateways if gateway.healthy]
    if not candidates:
        return []
    total_samples = sum(int(stats["sample_count"]) for stats in feedback_stats.values())
    unseen = [gateway for gateway in candidates if gateway.gateway_id not in feedback_stats]
    if unseen:
        return [
            {
                "gateway_id": gateway.gateway_id,
                "name": gateway.name,
                "score": 2.0,
                "success_rate": gateway.success_rate,
                "latency_ms": gateway.latency_ms,
                "cost_units": gateway.cost_units,
                "sample_count": 0,
                "reasons": ["Gateway has no recorded feedback yet; selected for exploration."],
            }
            for gateway in unseen
        ]
    ranked: list[dict[str, Any]] = []
    for gateway in candidates:
        stats = feedback_stats[gateway.gateway_id]
        count = int(stats["sample_count"])
        empirical_rate = float(stats["success_rate"])
        exploration_bonus = math.sqrt(2.0 * math.log(max(total_samples, 1)) / count)
        score = empirical_rate + exploration_bonus
        ranked.append({
            "gateway_id": gateway.gateway_id,
            "name": gateway.name,
            "score": round(score, 6),
            "success_rate": empirical_rate,
            "latency_ms": float(stats.get("avg_latency_ms", gateway.latency_ms)),
            "cost_units": gateway.cost_units,
            "sample_count": count,
            "reasons": [
                f"Observed success rate: {empirical_rate:.1%} over {count} feedback samples.",
                f"UCB exploration bonus: {exploration_bonus:.3f}.",
            ],
        })
    return sorted(ranked, key=lambda item: (-item["score"], item["gateway_id"]))
