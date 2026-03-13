import importlib
import sys
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

    monkeypatch.setitem(
        sys.modules,
        "rgbmatrix",
        types.SimpleNamespace(RGBMatrixOptions=DummyOptions, graphics=DummyGraphics),
    )


def _import_data_fresh(monkeypatch):
    _install_rgbmatrix_stub(monkeypatch)
    if "config" in sys.modules:
        del sys.modules["config"]
    if "data" in sys.modules:
        del sys.modules["data"]
    return importlib.import_module("data")


def test_offline_keeps_last_valid_btc_snapshot(monkeypatch):
    data = _import_data_fresh(monkeypatch)

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    calls = {"n": 0}

    def fake_get(url, timeout=0, **_kwargs):
        if "BTCUSDT" in url:
            if calls["n"] == 0:
                calls["n"] += 1
                return FakeResp({"lastPrice": "50000", "priceChangePercent": "1.5"})
            raise OSError("network down")
        if "generate_204" in url:
            raise OSError("offline")
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(data.http_client, "get", fake_get)

    data.fetch_btc_only()
    snap_ok = data.get_state_snapshot()
    usd_ok = snap_ok["bitcoin"]["usd"]

    data.fetch_btc_only()
    snap_offline = data.get_state_snapshot()

    assert snap_offline["bitcoin"]["usd"] == usd_ok
    assert snap_offline["status"]["btc"] is False
    assert snap_offline["conexao"] is False


def test_staleness_indicator_text(monkeypatch):
    data = _import_data_fresh(monkeypatch)

    with data.STATE_LOCK:
        data.dados.setdefault("freshness", {}).setdefault("last_ok", {})["btc"] = time.time() - (data.TTL_POLICY_S["btc"] + 10)
        data._refresh_snapshot_locked()

    stale = data.get_stale_info(keys=["btc"])

    assert stale["is_stale"] is True
    assert "btc" in stale["keys"]
    assert stale["text"].startswith("stale")


def test_cache_snapshot_reload(monkeypatch, tmp_path):
    data = _import_data_fresh(monkeypatch)

    monkeypatch.setattr(data, "SNAPSHOT_CACHE_PATH", str(tmp_path / ".runtime_snapshot.json"))

    with data.STATE_LOCK:
        data.dados["bitcoin"]["usd"] = 42424.0
        data.dados["bitcoin"]["brl"] = 200000.0
        data.dados["status"]["btc"] = True
        data._mark_data_ok_locked("btc")
        data._refresh_snapshot_locked()

    data._persist_snapshot_if_needed(force=True)

    with data.STATE_LOCK:
        data.dados["bitcoin"]["usd"] = 0
        data.dados["bitcoin"]["brl"] = 0
        data.dados["status"]["btc"] = False
        data._refresh_snapshot_locked()

    loaded = data._load_cached_snapshot()
    snap = data.get_state_snapshot()

    assert loaded is True
    assert snap["bitcoin"]["usd"] == 42424.0
    assert snap["status"]["btc"] is True
