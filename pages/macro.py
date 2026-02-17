from rgbmatrix import graphics
import config as cfg
import utils
import data

def draw(canv):
    st = data.dados['stocks']
    
    # --- 1. DESTAQUE: NASDAQ (Tech) ---
    # Nome (NDX é a sigla comum para Nasdaq 100)
    utils.draw_bold(canv, cfg.font_m, 1, 16, cfg.C_ORANGE, "NDX")
    
    nas_val = st['nasdaq']
    nas_var = st['nasdaq_var']
    nas_up = st['nasdaq_var'] >= 0
    
    utils.draw_arrow(canv, 20, 12, nas_up)
    cor_nas = cfg.C_GREEN if nas_up else cfg.C_RED
    graphics.DrawText(canv, cfg.font_s, 34, 15, cor_nas, f"{nas_var:+.1f}%")

    # Preço Grande
    str_num = f"{nas_val:,.0f}".replace(",", ".")
    w_num = sum(cfg.font_l.CharacterWidth(ord(c)) for c in str_num)
    x_base = (64 - w_num) // 2
    utils.draw_bold(canv, cfg.font_l, x_base, 26, cfg.C_WHITE, str_num)

    # Divisória
    graphics.DrawLine(canv, 0, 30, 63, 30, cfg.C_GREY)

    # --- 2. SECUNDÁRIOS ---
    # DXY (Índice Dólar)
    dxy_val = st['dxy']
    dxy_var = st['dxy_var']
    dxy_up = st['dxy_var'] >= 0
    
    graphics.DrawText(canv, cfg.font_s, 1, 39, cfg.C_WHITE, "DXY ($)")
    utils.draw_arrow(canv, 32, 35, dxy_up)
    cor_dxy = cfg.C_GREEN if dxy_up else cfg.C_RED 
    graphics.DrawText(canv, cfg.font_s, 40, 39, cor_dxy, f"{dxy_var:+.1f}%")
    
    # Valor DXY
    graphics.DrawText(canv, cfg.font_s, 1, 48, cfg.C_DIM, f"{dxy_val:.2f}".replace(".", ","))
