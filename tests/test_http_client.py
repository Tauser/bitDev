import pytest
import requests

from infra.http_client import HttpClient


class DummyResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_retry_on_429_then_success(monkeypatch):
    client = HttpClient(timeout=0.1, retries=2, backoff=0.01)
    calls = []
    sleeps = []

    responses = [DummyResponse(429), DummyResponse(429), DummyResponse(200)]

    def fake_request(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(client.session, "request", fake_request)
    monkeypatch.setattr("infra.http_client.time.sleep", lambda d: sleeps.append(d))

    response = client.get("https://example.test")

    assert response.status_code == 200
    assert len(calls) == 3
    assert sleeps == [0.01, 0.02]


def test_retry_on_5xx_then_success(monkeypatch):
    client = HttpClient(timeout=0.1, retries=1, backoff=0.02)
    calls = []
    sleeps = []

    responses = [DummyResponse(503), DummyResponse(200)]

    def fake_request(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(client.session, "request", fake_request)
    monkeypatch.setattr("infra.http_client.time.sleep", lambda d: sleeps.append(d))

    response = client.get("https://example.test/health")

    assert response.status_code == 200
    assert len(calls) == 2
    assert sleeps == [0.02]


def test_timeout_raises_after_retry(monkeypatch):
    client = HttpClient(timeout=0.1, retries=1, backoff=0.01)
    sleeps = []
    calls = {"n": 0}

    def fake_request(**_kwargs):
        calls["n"] += 1
        raise requests.exceptions.Timeout("slow")

    monkeypatch.setattr(client.session, "request", fake_request)
    monkeypatch.setattr("infra.http_client.time.sleep", lambda d: sleeps.append(d))

    with pytest.raises(requests.exceptions.Timeout):
        client.get("https://example.test/timeout")

    assert calls["n"] == 2
    assert sleeps == [0.01]


def test_request_uses_default_headers_and_timeout(monkeypatch):
    client = HttpClient(timeout=1.5, retries=0, backoff=0)
    captured = {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return DummyResponse(200)

    monkeypatch.setattr(client.session, "request", fake_request)

    response = client.get("https://example.test/data")

    assert response.status_code == 200
    assert captured["timeout"] == 1.5
    assert "User-Agent" in client.session.headers