import importlib
import sys
import types

import pytest
import requests


def _install_rgbmatrix_stub(monkeypatch):
    class DummyFont:
        def LoadFont(self, *_args, **_kwargs):
            return None

    class DummyColor:
        def __init__(self, r=0, g=0, b=0):
            self.red = r
            self.green = g
            self.blue = b

    class DummyGraphics:
        Font = DummyFont

        @staticmethod
        def Color(r, g, b):
            return DummyColor(r, g, b)

    class DummyOptions:
        pass

    dummy_module = types.SimpleNamespace(
        RGBMatrixOptions=DummyOptions,
        graphics=DummyGraphics,
    )
    monkeypatch.setitem(sys.modules, "rgbmatrix", dummy_module)


def _import_data(monkeypatch):
    _install_rgbmatrix_stub(monkeypatch)
    if "config" in sys.modules:
        del sys.modules["config"]
    if "data" in sys.modules:
        del sys.modules["data"]
    return importlib.import_module("data")


def test_fetch_btc_only_api_indisponivel_mantem_fallback_offline(monkeypatch):
    data = _import_data(monkeypatch)

    def fake_get(url, timeout=0, **_kwargs):
        if "api.binance.com" in url:
            raise requests.exceptions.ConnectionError("binance offline")
        if "clients3.google.com/generate_204" in url:
            raise requests.exceptions.ConnectionError("internet offline")
        raise AssertionError(f"url inesperada: {url}")

    monkeypatch.setattr(data.http_client, "get", fake_get)

    data.fetch_btc_only()
    snap = data.get_state_snapshot()

    assert snap["status"]["btc"] is False
    assert snap["conexao"] is False


def test_fetch_btc_only_json_invalido_preserva_fallback_com_internet(monkeypatch):
    data = _import_data(monkeypatch)

    class BadJsonResponse:
        def json(self):
            raise ValueError("json invalido")

    class OkResponse:
        def json(self):
            return {}

    def fake_get(url, timeout=0, **_kwargs):
        if "api.binance.com" in url:
            return BadJsonResponse()
        if "clients3.google.com/generate_204" in url:
            return OkResponse()
        raise AssertionError(f"url inesperada: {url}")

    monkeypatch.setattr(data.http_client, "get", fake_get)

    data.fetch_btc_only()
    snap = data.get_state_snapshot()

    assert snap["status"]["btc"] is False
    assert snap["conexao"] is True

