from providers import stocks as stocks_provider


class DummyClient:
    def get(self, _url, **_kwargs):
        payload = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "regularMarketPrice": 110.0,
                            "chartPreviousClose": 100.0,
                        }
                    }
                ]
            }
        }
        return type("Resp", (), {"json": lambda _self: payload})()


def test_fetch_stocks_updates_expected_fields():
    state = {
        "stocks": {"ibov": 0, "ibov_var": 0, "sp500": 0, "sp500_var": 0, "nasdaq": 0, "nasdaq_var": 0},
        "status": {"stocks": False},
    }

    stocks_provider.fetch_stocks(state, DummyClient())

    assert state["stocks"]["ibov"] == 110.0
    assert state["stocks"]["sp500"] == 110.0
    assert state["stocks"]["nasdaq"] == 110.0
    assert round(state["stocks"]["ibov_var"], 2) == 10.0
    assert state["status"]["stocks"] is True