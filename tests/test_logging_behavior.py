import importlib
import logging
import sys
import types

import requests

from infra.logging_config import get_logger


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


def test_logging_nominal_records_structured_message(caplog):
    logger = get_logger("tests.logging")

    with caplog.at_level(logging.INFO):
        logger.info("op=healthcheck status=ok")

    messages = [r.getMessage() for r in caplog.records]
    assert any("op=healthcheck" in msg and "status=ok" in msg for msg in messages)


def test_fetch_btc_only_logs_warning_on_api_error(monkeypatch, caplog):
    data = _import_data(monkeypatch)

    def fake_get(url, timeout=0, **_kwargs):
        if "api.binance.com" in url:
            raise requests.exceptions.ConnectionError("binance offline")
        if "clients3.google.com/generate_204" in url:
            return object()
        raise AssertionError(f"url inesperada: {url}")

    monkeypatch.setattr(data.http_client, "get", fake_get)

    with caplog.at_level(logging.WARNING):
        data.fetch_btc_only()

    messages = [r.getMessage() for r in caplog.records]
    assert any("op=fetch_btc_only" in msg and "status=failed" in msg for msg in messages)