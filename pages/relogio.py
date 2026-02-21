import time
from rgbmatrix import graphics
import config as cfg
import utils

def draw(canv):
    now = time.localtime()
    
    # Cores do Tema
    c_time = cfg.C_WHITE
    c_date = cfg.C_ORANGE
    c_sec  = cfg.C_TEAL
    c_dim  = cfg.C_GREY
    
    # --- 1. DATA (Topo) ---
    # Mapeamento manual para garantir PT-BR sem depender de locale do sistema
    dias = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]
    meses = ["", "JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
    
    dia_sem = dias[now.tm_wday]
    dia_num = now.tm_mday
    mes_nome = meses[now.tm_mon]
    
    # Ex: "SEX, 24 FEV"
    data_str = f"{dia_sem}, {dia_num} {mes_nome}"
    utils.draw_center(canv, cfg.font_s, 10, c_date, data_str)
    
    # --- 2. HORA (Centro - Grande) ---
    hora = f"{now.tm_hour:02d}"
    minuto = f"{now.tm_min:02d}"
    
    # Efeito de piscar os dois pontos (:) a cada segundo
    if int(time.time() * 2) % 2 == 0:
        graphics.DrawText(canv, cfg.font_xl, 28, 35, c_dim, ":")
        
    # Desenha Hora e Minuto com espaçamento ajustado
    # font_xl (10x20) ocupa aprox 20px para 2 digitos
    graphics.DrawText(canv, cfg.font_xl, 6, 35, c_time, hora)
    graphics.DrawText(canv, cfg.font_xl, 38, 35, c_time, minuto)
    
    # --- 3. SEGUNDOS (Baixo) ---
    seg = f"{now.tm_sec:02d}"
    utils.draw_center(canv, cfg.font_l, 52, c_sec, seg)
    
    # --- 4. BARRA DE PROGRESSO (Rodapé) ---
    # Uma linha fina que cresce conforme os segundos passam
    w_bar = int((now.tm_sec / 60) * 64)
    if w_bar > 0:
        graphics.DrawLine(canv, 0, 63, w_bar, 63, c_sec)
