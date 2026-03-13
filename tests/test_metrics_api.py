import importlib
import sys

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


def test_api_metrics_contract(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "_get_runtime_metrics",
        lambda: {
            "runtime": {
                "ready": True,
                "collector_alive": True,
                "snapshot_ready": True,
                "tick_age_s": 0.1,
                "collector_started": True,
            },
            "freshness": {
                "has_stale": False,
                "stale": {},
                "age_s": {},
                "ttl_s": {"btc": 20},
                "offline_since": None,
            },
            "providers": {
                "btc": {
                    "attempts": 1,
                    "success": 1,
                    "errors": 0,
                    "last_ok": 1.0,
                    "last_error": "",
                    "last_duration_ms": 50,
                }
            },
        },
    )

    response = client.get("/api/metrics")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["service"] == "cryptomonitor"
    assert isinstance(payload["uptime_s"], int)
    assert "runtime" in payload
    assert "freshness" in payload
    assert "providers" in payload
    assert payload["providers"]["btc"]["last_duration_ms"] == 50
