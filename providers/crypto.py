def get_color(symbol, cfg):
    sym = symbol.upper()
    if sym == "BTC":
        return cfg.C_ORANGE
    if sym == "ETH":
        return cfg.C_BLUE
    if sym == "SOL":
        try:
            from rgbmatrix import graphics
            return graphics.Color(153, 69, 255)
        except Exception:
            return cfg.C_BLUE
    if sym == "ADA":
        try:
            from rgbmatrix import graphics
            return graphics.Color(0, 51, 173)
        except Exception:
            return cfg.C_BLUE
    if sym == "DOGE":
        return cfg.C_GOLD
    if sym == "XRP":
        return cfg.C_WHITE
    if sym == "BNB":
        return cfg.C_YELLOW
    return cfg.C_TEAL


def fetch_btc_only(state, http_client, check_internet_fn, logger):
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
        payload = http_client.get(url, timeout=5).json()

        price = float(payload["lastPrice"])
        change = float(payload["priceChangePercent"])

        state["bitcoin"]["usd"] = price
        state["bitcoin"]["change"] = change
        state["bitcoin"]["brl"] = price * state["usdtbrl"]
        state["conexao"] = True
        state["status"]["btc"] = True
    except Exception as exc:
        logger.warning("op=fetch_btc_only status=failed reason=%s", exc)
        state["status"]["btc"] = False
        state["conexao"] = bool(check_internet_fn())


def fetch_secondary_coins(state, http_client, color_resolver):
    temp_list = []

    for symbol in state["moedas_ativas"]:
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}USDT"
            payload = http_client.get(url, timeout=2).json()

            temp_list.append(
                {
                    "s": symbol.upper(),
                    "p": float(payload["lastPrice"]),
                    "c": float(payload["priceChangePercent"]),
                    "col": color_resolver(symbol),
                }
            )
        except Exception:
            pass

    state["secondary"] = temp_list


def fetch_extras(state, http_client, get_wifi_signal_fn):
    try:
        payload = http_client.get("https://economia.awesomeapi.com.br/last/USD-BRL", timeout=2).json()
        state["usdtbrl"] = float(payload["USDBRL"]["bid"])
    except Exception:
        pass

    try:
        payload = http_client.get("https://api.alternative.me/fng/", timeout=2).json()
        state["fg_val"] = int(payload["data"][0]["value"])
        state["wifi_signal"] = get_wifi_signal_fn()
    except Exception:
        pass