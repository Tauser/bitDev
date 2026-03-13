import importlib
import sys
import time

import pytest


@pytest.fixture()
def app_module(monkeypatch):
    monkeypatch.setenv("BITDEV_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("BITDEV_FLASK_SECRET_KEY", "test-flask-secret")

    if "app" in sys.modules:
        del sys.modules["app"]

    module = importlib.import_module("app")
    module.app.config.update(TESTING=True)
    return module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


def test_api_health_contract_and_status(client):
    t0 = time.perf_counter()
    response = client.get("/api/health")
    elapsed = time.perf_counter() - t0

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "status": "ok",
        "service": "cryptomonitor",
        "alive": True,
    }
    assert elapsed < 0.1


def test_api_ready_when_ready_returns_200_and_contract(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "_get_runtime_readiness",
        lambda: {
            "ready": True,
            "collector_alive": True,
            "snapshot_ready": True,
            "tick_age_s": 0.123,
        },
    )

    response = client.get("/api/ready")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload == {
        "status": "ready",
        "ready": True,
        "collector_alive": True,
        "snapshot_ready": True,
        "tick_age_s": 0.123,
    }


def test_api_ready_when_not_ready_returns_503_and_contract(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "_get_runtime_readiness",
        lambda: {
            "ready": False,
            "collector_alive": False,
            "snapshot_ready": False,
            "tick_age_s": None,
        },
    )

    response = client.get("/api/ready")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload == {
        "status": "not_ready",
        "ready": False,
        "collector_alive": False,
        "snapshot_ready": False,
        "tick_age_s": None,
    }

