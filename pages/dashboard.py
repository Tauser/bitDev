import time
from rgbmatrix import graphics
import config as cfg
import utils
import data
import animations

# --- ESTADO LOCAL DA PÁGINA ---
slide_secundarias_idx = 0
last_slide_time = time.time()
anim_saitama_idx = 0
last_anim_saitama_time = time.time()

# Carrega recursos (GIF) apenas uma vez ao importar
frames_saitama = animations.carregar_gif(cfg.ANIMACAO_FILE, cfg.ANIMACAO_W, cfg.ANIMACAO_H)

def init():
    global slide_secundarias_idx, last_slide_time
    slide_secundarias_idx = 0
    last_slide_time = time.time()

def draw(canv):
    global slide_secundarias_idx, last_slide_time, anim_saitama_idx, last_anim_saitama_time

    # Animação
    if frames_saitama and (time.time() - last_anim_saitama_time > cfg.GIF_SPEED):
        anim_saitama_idx = (anim_saitama_idx + 1) % len(frames_saitama)
        last_anim_saitama_time = time.time()

    # 2. BITCOIN
    utils.draw_bold(canv, cfg.font_m, 1, 16, cfg.C_ORANGE, "BTC")
    btc_data = data.dados["bitcoin"]
    btc_up = btc_data["change"] >= 0
    utils.draw_arrow(canv, 20, 12, btc_up)
    cor_pct = cfg.C_GREEN if btc_up else cfg.C_RED
    graphics.DrawText(canv, cfg.font_s, 38, 15, cor_pct, f"{btc_data['change']:+.2f}%")
    
    val_usd = btc_data['usd']
    symbol = "$"
    str_num = f"{val_usd:,.2f}"
    w_sym = cfg.font_l.CharacterWidth(ord(symbol))
    w_num = sum(cfg.font_l.CharacterWidth(ord(c)) for c in str_num)
    total_width = w_sym + w_num

    if total_width > 63:
        str_num = f"{val_usd:,.0f}"
        w_num = sum(cfg.font_l.CharacterWidth(ord(c)) for c in str_num)
        total_width = w_sym + w_num

    x_base = (64 - total_width) // 2
    graphics.DrawText(canv, cfg.font_l, x_base, 26, cfg.C_WHITE, symbol)
    utils.draw_bold(canv, cfg.font_l, x_base + w_sym, 26, cfg.C_WHITE, str_num)
    
    # Real
    val_brl = btc_data['brl']
    txt_brl = f"R$ {val_brl:,.2f}".replace(",", ".")
    utils.draw_center(canv, cfg.font_s, 35, cfg.C_YELLOW, txt_brl)
    
    graphics.DrawLine(canv, 0, 38, 63, 38, cfg.C_GREY)

    # MOEDAS SECUNDÁRIAS 
    sec = data.dados["secondary"]
    qtd = len(sec)
    
    if slide_secundarias_idx * 2 >= qtd:
        slide_secundarias_idx = 0

    if qtd > 0:
        if time.time() - last_slide_time > cfg.TEMPO_SLIDE:
            slide_secundarias_idx += 1
            if slide_secundarias_idx * 2 >= qtd: 
                slide_secundarias_idx = 0
            last_slide_time = time.time()
        
        base_i = slide_secundarias_idx * 2
        y_sym, y_prc, y_pct = 45, 51, 57

        # --- Coluna 1 ---
        if base_i < qtd:
            m1 = sec[base_i]
            graphics.DrawText(canv, cfg.font_s, 1, y_sym, m1["col"], m1["s"])
            utils.draw_arrow(canv, 25, y_sym-3, m1["c"] >= 0)
            
            if m1["p"] > 1000: p_fmt = f"{m1['p']:,.0f}".replace(",",".")
            elif m1["p"] < 1:  p_fmt = f"{m1['p']:.4f}".replace(".",",")
            else:              p_fmt = f"{m1['p']:.2f}".replace(".",",")
            
            graphics.DrawText(canv, cfg.font_s, 1, y_prc, cfg.C_WHITE, p_fmt)
            cor_m1 = cfg.C_GREEN if m1["c"] >= 0 else cfg.C_RED
            graphics.DrawText(canv, cfg.font_s, 1, y_pct, cor_m1, f"{m1['c']:+.1f}%")

        # Divisória
        graphics.DrawLine(canv, 31, 40, 31, 57, cfg.C_GREY)

        # --- Coluna 2 ---
        if base_i + 1 < qtd:
            m2 = sec[base_i + 1]
            off = 34
            graphics.DrawText(canv, cfg.font_s, off, y_sym, m2["col"], m2["s"])
            utils.draw_arrow(canv, off+24, y_sym-3, m2["c"] >= 0)
            
            if m2["p"] > 1000: p_fmt = f"{m2['p']:,.0f}".replace(",",".")
            elif m2["p"] < 1:  p_fmt = f"{m2['p']:.4f}".replace(".",",")
            else:              p_fmt = f"{m2['p']:.2f}".replace(".",",")
            
            graphics.DrawText(canv, cfg.font_s, off, y_prc, cfg.C_WHITE, p_fmt)
            cor_m2 = cfg.C_GREEN if m2["c"] >= 0 else cfg.C_RED
            graphics.DrawText(canv, cfg.font_s, off, y_pct, cor_m2, f"{m2['c']:+.1f}%")
        else:
            # Slot Vazio -> Saitama
            if frames_saitama:
                canv.SetImage(frames_saitama[anim_saitama_idx], 34, 39)
