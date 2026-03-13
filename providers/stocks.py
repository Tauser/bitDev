
def fetch_stocks(state, http_client):
    headers = {"User-Agent": "Mozilla/5.0"}

    def get_ticker(symbol, key_price, key_var):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            payload = http_client.get(url, headers=headers, timeout=2).json()
            meta = payload["chart"]["result"][0]["meta"]
            price = meta["regularMarketPrice"]
            prev = meta["chartPreviousClose"]
            state["stocks"][key_price] = price
            state["stocks"][key_var] = ((price - prev) / prev) * 100
            state["status"]["stocks"] = True
        except Exception:
            pass

    get_ticker("^BVSP", "ibov", "ibov_var")
    get_ticker("^GSPC", "sp500", "sp500_var")
    get_ticker("^IXIC", "nasdaq", "nasdaq_var")