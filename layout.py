import time
from rgbmatrix import graphics
import config as cfg
import utils
import data

pos_scroll = 64

def draw_header(canv, title=None, text_color=cfg.C_TEAL):
    for y in range(9): 
        graphics.DrawLine(canv, 0, y, 63, y, cfg.C_BG_HEADER)
    
    if title:
        utils.draw_center(canv, cfg.font_s, 6, text_color, title)
    else:
        graphics.DrawText(canv, cfg.font_s, 1, 6, text_color, time.strftime("%d/%m"))
        utils.draw_center(canv, cfg.font_s, 6, cfg.C_WHITE, f"{data.dados['temp']}\u00b0C")
        
        sig = data.dados.get('wifi_signal', 0)
        if sig < -70 and sig != 0:
            graphics.DrawText(canv, cfg.font_s, 39, 6, cfg.C_WHITE, time.strftime("%H:%M"))
            graphics.DrawLine(canv, 60, 5, 60, 2, cfg.C_RED); graphics.DrawLine(canv, 61, 5, 61, 3, cfg.C_RED); graphics.DrawLine(canv, 62, 5, 62, 4, cfg.C_RED)
        else:
            graphics.DrawText(canv, cfg.font_s, 44, 6, cfg.C_WHITE, time.strftime("%H:%M"))
        
    graphics.DrawLine(canv, 0, 8, 63, 8, cfg.C_GREY)

def draw_footer(canv):
    global pos_scroll
    
    graphics.DrawLine(canv, 0, 58, 63, 58, cfg.C_GREY)
    
    notif = data.get_active_notification()
    
    msg_custom = data.dados.get('msg_custom', '')
    
    if notif:
        parts = [(notif['msg'], notif['color'])]
    elif msg_custom:
        parts = [(msg_custom, cfg.C_YELLOW)]
    else:
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
