import time
from rgbmatrix import graphics
import config as cfg
import utils
import data

# Estado do Scroll do Rodapé (agora compartilhado entre todas as telas)
pos_scroll = 64

def draw_header(canv, title=None):
    """Desenha o cabeçalho. Se title for None, mostra Data/Temp/Hora."""
    # Fundo do Header
    for y in range(9): 
        graphics.DrawLine(canv, 0, y, 63, y, cfg.C_BG_HEADER)
    
    if title:
        # Título Específico (Ex: MERCADO, MACRO)
        utils.draw_center(canv, cfg.font_s, 6, cfg.C_TEAL, title)
    else:
        # Header Padrão (Dashboard)
        graphics.DrawText(canv, cfg.font_s, 1, 6, cfg.C_TEAL, time.strftime("%d/%m"))
        utils.draw_center(canv, cfg.font_s, 6, cfg.C_WHITE, f"{data.dados['temp']}\u00b0C")
        graphics.DrawText(canv, cfg.font_s, 44, 6, cfg.C_WHITE, time.strftime("%H:%M"))
        
    # Linha separadora
    graphics.DrawLine(canv, 0, 8, 63, 8, cfg.C_GREY)

def draw_footer(canv):
    """Desenha o rodapé com ticker de cotações"""
    global pos_scroll
    
    # Linha separadora
    graphics.DrawLine(canv, 0, 58, 63, 58, cfg.C_GREY)
    
    # Verifica se tem mensagem personalizada
    msg = data.dados.get('msg_custom', '')
    if msg:
        parts = [(msg, cfg.C_YELLOW)]
    else:
        # Rodapé Padrão (Cotações)
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
