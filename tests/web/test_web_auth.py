import importlib
import sys

import pytest


ADMIN_TOKEN = "test-admin-token"
PROTECTED_ROUTES = [
    ("GET", "/reiniciar", None),
    ("GET", "/desligar", None),
    ("GET", "/wifi_reset", None),
    ("POST", "/salvar_wifi", {"ssid": "MinhaRede", "psk": "senha123"}),
    ("GET", "/logs", None),
]


@pytest.fixture()
def app_module(monkeypatch):
    monkeypatch.setenv("BITDEV_ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BITDEV_FLASK_SECRET_KEY", "test-flask-secret")

    if "app" in sys.modules:
        del sys.modules["app"]

    module = importlib.import_module("app")
    module.app.config.update(TESTING=True)
    return module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


def _request(client, method, path, data=None, headers=None):
    if method == "POST":
        return client.post(path, data=data or {}, headers=headers or {})
    return client.get(path, headers=headers or {})


@pytest.mark.parametrize("method,path,data", PROTECTED_ROUTES)
def test_web_routes_without_token_return_401(client, method, path, data):
    response = _request(client, method, path, data=data)
    assert response.status_code == 401


@pytest.mark.parametrize("method,path,data", PROTECTED_ROUTES)
def test_web_routes_with_invalid_token_return_403(client, method, path, data):
    response = _request(
        client,
        method,
        path,
        data=data,
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 403


def test_web_logs_with_valid_token_return_200(client, app_module, monkeypatch):
    monkeypatch.setattr(
        app_module.subprocess,
        "check_output",
        lambda *args, **kwargs: b"line1\\nline2\\n",
    )

    response = client.get(
        "/logs",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )

    assert response.status_code == 200
    assert "line1" in response.get_data(as_text=True)
