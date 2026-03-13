import importlib
import itertools
import sys
import threading
import time
import types


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


def test_state_snapshot_consistency_under_concurrency(monkeypatch):
    _install_rgbmatrix_stub(monkeypatch)

    if "config" in sys.modules:
        del sys.modules["config"]
    if "data" in sys.modules:
        del sys.modules["data"]

    data = importlib.import_module("data")

    counter = itertools.count(1)

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    def fake_get(url, timeout=0, **_kwargs):
        if "BTCUSDT" in url:
            n = next(counter)
            return FakeResp({"lastPrice": str(10000 + n), "priceChangePercent": str(n % 5)})
        if "generate_204" in url:
            return FakeResp({})
        raise AssertionError(f"unexpected URL in test: {url}")

    monkeypatch.setattr(data.http_client, "get", fake_get)

    errors = []

    def writer():
        try:
            for _ in range(80):
                data.fetch_btc_only()
                data.add_notification("ok")
                time.sleep(0.001)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    def reader():
        try:
            for _ in range(1200):
                snap = data.get_state_snapshot()
                btc = snap["bitcoin"]
                usd = float(btc["usd"])
                brl = float(btc["brl"])
                usdtbrl = float(snap["usdtbrl"])
                assert abs(brl - (usd * usdtbrl)) < 1e-6
                assert isinstance(snap.get("notifications", []), list)
        except Exception as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=writer) for _ in range(3)]
    threads += [threading.Thread(target=reader) for _ in range(2)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"unexpected concurrency errors: {errors}"

