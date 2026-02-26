import time
from rgbmatrix import graphics
import config as cfg
import utils
import data
import animations
import layout

# --- ESTADO LOCAL DA PÁGINA ---
pos_scroll = 64
slide_secundarias_idx = 0
last_slide_time = time.time()
anim_saitama_idx = 0
last_anim_saitama_time = time.time()

# Carrega recursos (GIF) apenas uma vez ao importar
frames_saitama = animations.carregar_gif(cfg.ANIMACAO_FILE, cfg.ANIMACAO_W, cfg.ANIMACAO_H)

def draw(canv):
    global pos_scroll, slide_secundarias_idx, last_slide_time, anim_saitama_idx, last_anim_saitama_time

    # Animação Saitama
    if frames_saitama and (time.time() - last_anim_saitama_time > cfg.GIF_SPEED):
        anim_saitama_idx = (anim_saitama_idx + 1) % len(frames_saitama)
        last_anim_saitama_time = time.time()

    # 1. HEADER
    layout.draw_header(canv, None, cfg.C_TEAL)

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
    
    if qtd > 0:
        # Lógica de Rotação (A cada TEMPO_SLIDE segundos)
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

    # 4. RODAPÉ
    graphics.DrawLine(canv, 0, 58, 63, 58, cfg.C_GREY)
    
    fg = data.dados["fg_val"]
    fg_col = cfg.C_GREEN if fg > 60 else (cfg.C_RED if fg < 30 else cfg.C_YELLOW)
    
    val_usdt = data.dados['usdtbrl']
    usdt_fmt = f"R$ {val_usdt:.2f}".replace(".", ",")
    
    parts = [
        ("F&G:", cfg.C_DIM), (f"{fg}", fg_col),
        (" | USDT:", cfg.C_DIM), (f"{usdt_fmt}", cfg.C_GREEN),
        (" | ", cfg.C_DIM), ("BITDEV", cfg.C_TEAL)
    ]
    
    curr_x = pos_scroll
    txt_len = 0
    for txt, color in parts:
        l = graphics.DrawText(canv, cfg.font_s, curr_x, 64, color, txt)
        curr_x += l
        txt_len += l
    
    pos_scroll -= 1
    if pos_scroll + txt_len < 0: pos_scroll = 64
import os
import random
import time
from rgbmatrix import graphics
import config as cfg
import utils
import animations
import data

# --- ESTADO LOCAL ---
frames_pixelart_cheio = []
anim_art_idx = 0
ultimo_gif_nome = "" 
last_frame_time = 0

def tem_imagens():
    try:
        pasta = os.path.join(cfg.BASE_DIR, "images/pixelart")
        if not os.path.exists(pasta): return False
        return any(f.lower().endswith('.gif') for f in os.listdir(pasta))
    except: return False

def sortear_novo():
    """Sorteia um novo GIF da pasta"""
    global frames_pixelart_cheio, anim_art_idx, ultimo_gif_nome
    pasta = os.path.join(cfg.BASE_DIR, "images/pixelart")
    
    if not os.path.exists(pasta):
        try: os.makedirs(pasta)
        except: pass
            
    gifs = [f for f in os.listdir(pasta) if f.lower().endswith('.gif')]
    
    if gifs:
        escolhido = random.choice(gifs)
        # Tenta não repetir o mesmo GIF seguido
        if len(gifs) > 1 and escolhido == ultimo_gif_nome:
            while escolhido == ultimo_gif_nome:
                escolhido = random.choice(gifs)
        
        ultimo_gif_nome = escolhido
        print(f"--> GIF Sorteado: {escolhido}")
        
        caminho_completo = os.path.join(pasta, escolhido)
        frames_pixelart_cheio = animations.carregar_gif(caminho_completo, 64, 64)
        anim_art_idx = 0
    else:
        frames_pixelart_cheio = []

def draw(canv):
    global anim_art_idx, last_frame_time
    
    speed = data.dados.get('gif_speed', 0.1)
    
    if frames_pixelart_cheio:
        try:
            canv.SetImage(frames_pixelart_cheio[anim_art_idx], 0, 0)
            if time.time() - last_frame_time > speed:
                anim_art_idx = (anim_art_idx + 1) % len(frames_pixelart_cheio)
                last_frame_time = time.time()
        except: pass
    else:
        graphics.DrawLine(canv, 0, 0, 63, 63, cfg.C_RED) 
        graphics.DrawLine(canv, 63, 0, 0, 63, cfg.C_RED)
        utils.draw_center(canv, cfg.font_s, 25, cfg.C_WHITE, "PASTA")
        utils.draw_center(canv, cfg.font_s, 35, cfg.C_WHITE, "VAZIA")
