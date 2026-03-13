import importlib
import sys
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


def test_snapshot_contract_minimal(monkeypatch):
    _install_rgbmatrix_stub(monkeypatch)

    if "config" in sys.modules:
        del sys.modules["config"]
    if "data" in sys.modules:
        del sys.modules["data"]

    data = importlib.import_module("data")
    snap = data.get_state_snapshot()

    assert isinstance(snap, dict)
    for key in ("bitcoin", "status", "freshness", "stocks", "printer", "weather"):
        assert key in snap

    freshness = snap["freshness"]
    assert "ttl_s" in freshness
    assert "stale" in freshness
    assert "age_s" in freshness
