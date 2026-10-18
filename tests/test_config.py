from pathlib import Path

import pytest

from routewise.config import Settings, load_gateways


def test_gateway_configuration_loads_three_unique_gateways():
    path = Path(__file__).resolve().parents[1] / "config" / "gateways.json"
    gateways, routing = load_gateways(path)
    assert len(gateways) == 3
    assert len({gateway.gateway_id for gateway in gateways}) == 3
    assert routing["success_weight"] == 0.70


def test_settings_reject_all_zero_weights():
    settings = Settings("db", "gateways",  success_weight=0, latency_weight=0, cost_weight=0)
    with pytest.raises(ValueError):
        settings.validate()
