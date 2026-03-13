from providers import crypto as crypto_provider


class DummyClient:
    def __init__(self, payload=None, should_fail=False):
        self.payload = payload or {}
        self.should_fail = should_fail

    def get(self, _url, timeout=0, **_kwargs):
        if self.should_fail:
            raise RuntimeError("offline")
        return type("Resp", (), {"json": lambda _self: self.payload})()


class DummyLogger:
    def warning(self, *_args, **_kwargs):
        return None


def test_fetch_btc_only_success_updates_state():
    state = {
        "bitcoin": {"usd": 0, "brl": 0, "change": 0},
        "usdtbrl": 5.0,
        "conexao": False,
        "status": {"btc": False},
    }
    payload = {"lastPrice": "100", "priceChangePercent": "1.5"}

    crypto_provider.fetch_btc_only(state, DummyClient(payload), lambda: False, DummyLogger())

    assert state["bitcoin"]["usd"] == 100.0
    assert state["bitcoin"]["brl"] == 500.0
    assert state["bitcoin"]["change"] == 1.5
    assert state["conexao"] is True
    assert state["status"]["btc"] is True


def test_fetch_btc_only_failure_uses_internet_fallback():
    state = {
        "bitcoin": {"usd": 0, "brl": 0, "change": 0},
        "usdtbrl": 5.0,
        "conexao": True,
        "status": {"btc": True},
    }

    crypto_provider.fetch_btc_only(state, DummyClient(should_fail=True), lambda: False, DummyLogger())

    assert state["status"]["btc"] is False
    assert state["conexao"] is False


def test_fetch_secondary_and_extras():
    class MultiClient:
        def get(self, url, timeout=0, **_kwargs):
            if "BTCUSDT" in url:
                return type("Resp", (), {"json": lambda _self: {"lastPrice": "10", "priceChangePercent": "2"}})()
            if "USD-BRL" in url:
                return type("Resp", (), {"json": lambda _self: {"USDBRL": {"bid": "5.25"}}})()
            return type("Resp", (), {"json": lambda _self: {"data": [{"value": "50"}]}})()

    state = {
        "moedas_ativas": ["btc"],
        "secondary": [],
        "usdtbrl": 0,
        "fg_val": 0,
        "wifi_signal": 0,
    }

    crypto_provider.fetch_secondary_coins(state, MultiClient(), lambda _s: "C")
    crypto_provider.fetch_extras(state, MultiClient(), lambda: 73)

    assert state["secondary"][0]["s"] == "BTC"
    assert state["usdtbrl"] == 5.25
    assert state["fg_val"] == 50
    assert state["wifi_signal"] == 73