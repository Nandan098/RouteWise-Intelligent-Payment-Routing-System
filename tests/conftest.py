from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from routewise.api import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATEWAY_CONFIG = PROJECT_ROOT / "config" / "gateways.json"


@pytest.fixture
def app(tmp_path: Path):
    return create_app(database_path=tmp_path / "test-routewise.db", gateway_config_path=GATEWAY_CONFIG)


@pytest.fixture
def client(app):
    return TestClient(app)
