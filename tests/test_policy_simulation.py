from scripts.compare_policies import simulate


def test_policy_simulation_is_reproducible():
    assert simulate("ucb1", 100, 42) == simulate("ucb1", 100, 42)


def test_policy_simulation_reports_valid_rates():
    result = simulate("round_robin", 300, 7)
    assert result["transactions"] == 300
    assert 0 <= result["success_rate"] <= 1
    assert sum(result[f"routes_{gateway}"] for gateway in ("gateway_a", "gateway_b", "gateway_c")) == 300
