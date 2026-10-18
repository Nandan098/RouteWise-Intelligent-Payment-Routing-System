from routewise.adaptive import rank_ucb
from routewise.config import Gateway


def candidates():
    return [
        Gateway("a", "A", .98, 150, .02, True),
        Gateway("b", "B", .95, 100, .025, True),
        Gateway("c", "C", .99, 300, .035, True),
        Gateway("off", "Off", .99, 20, .001, False),
    ]


def test_ucb_explores_untried_healthy_gateways_first():
    ranked = rank_ucb(candidates(), {"a": {"sample_count": 3, "success_count": 2, "success_rate": 2 / 3, "avg_latency_ms": 150}})
    assert {row["gateway_id"] for row in ranked} == {"b", "c"}
    assert all(row["score"] == 2.0 for row in ranked)


def test_ucb_uses_success_rate_and_exploration_bonus_when_all_sampled():
    stats = {
        "a": {"sample_count": 20, "success_count": 18, "success_rate": .9, "avg_latency_ms": 150},
        "b": {"sample_count": 20, "success_count": 10, "success_rate": .5, "avg_latency_ms": 100},
        "c": {"sample_count": 2, "success_count": 2, "success_rate": 1.0, "avg_latency_ms": 300},
    }
    ranked = rank_ucb(candidates(), stats)
    assert ranked[0]["gateway_id"] == "c"
    assert ranked[0]["sample_count"] == 2
