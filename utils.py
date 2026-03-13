from rgbmatrix import graphics

_TEXT_WIDTH_CACHE = {}
_TEXT_WIDTH_CACHE_MAX = 512


def to_matrix_color(color):
    if isinstance(color, tuple):
        return graphics.Color(*color)
    return color


def text_width(font, text):
    s = str(text)
    key = (id(font), s)
    cached = _TEXT_WIDTH_CACHE.get(key)
    if cached is not None:
        return cached

    width = sum(font.CharacterWidth(ord(c)) for c in s)
    if len(_TEXT_WIDTH_CACHE) >= _TEXT_WIDTH_CACHE_MAX:
        _TEXT_WIDTH_CACHE.clear()
    _TEXT_WIDTH_CACHE[key] = width
    return width


def draw_center(canvas, font, y, color, text, shadow=False):
    text = str(text)
    x = (64 - text_width(font, text)) // 2

    if shadow:
        graphics.DrawText(canvas, font, x + 1, y + 1, graphics.Color(0, 0, 0), text)

    graphics.DrawText(canvas, font, x, y, to_matrix_color(color), text)


def draw_bold(canvas, font, x, y, color, text):
    c_obj = to_matrix_color(color)
    s = str(text)
    graphics.DrawText(canvas, font, x, y, c_obj, s)
    graphics.DrawText(canvas, font, x + 1, y, c_obj, s)


def draw_arrow(canvas, x, y, is_up):
    color = graphics.Color(0, 255, 0) if is_up else graphics.Color(255, 0, 0)

    if is_up:
        coords = [(x + 2, y), (x + 1, y + 1), (x + 3, y + 1), (x, y + 2), (x + 4, y + 2)]
    else:
        coords = [(x, y), (x + 4, y), (x + 1, y + 1), (x + 3, y + 1), (x + 2, y + 2)]

    for cx, cy in coords:
        canvas.SetPixel(cx, cy, color.red, color.green, color.blue)


def draw_text_shadow(canvas, font, x, y, color, text):
    c_shadow = graphics.Color(0, 0, 0)
    s = str(text)
    graphics.DrawText(canvas, font, x + 1, y + 1, c_shadow, s)
    graphics.DrawText(canvas, font, x, y, to_matrix_color(color), s)


def format_market_price(value):
    if value > 1000:
        return f"{value:,.0f}".replace(",", ".")
    if value < 1:
        return f"{value:.4f}".replace(".", ",")
    return f"{value:.2f}".replace(".", ",")


def draw_market_coin_column(canv, cfg, coin_data, x, y_sym, y_prc, y_pct, arrow_x):
    graphics.DrawText(canv, cfg.font_s, x, y_sym, to_matrix_color(coin_data["col"]), coin_data["s"])
    draw_arrow(canv, arrow_x, y_sym - 3, coin_data["c"] >= 0)

    graphics.DrawText(canv, cfg.font_s, x, y_prc, cfg.C_WHITE, format_market_price(coin_data["p"]))
    cor = cfg.C_GREEN if coin_data["c"] >= 0 else cfg.C_RED
    graphics.DrawText(canv, cfg.font_s, x, y_pct, cor, f"{coin_data['c']:+.1f}%")


def draw_no_images_placeholder(canv, cfg):
    graphics.DrawLine(canv, 0, 0, 63, 63, cfg.C_RED)
    graphics.DrawLine(canv, 63, 0, 0, 63, cfg.C_RED)
    draw_center(canv, cfg.font_s, 25, cfg.C_WHITE, "PASTA")
    draw_center(canv, cfg.font_s, 35, cfg.C_WHITE, "VAZIA")
