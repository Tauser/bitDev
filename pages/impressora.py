import time
from rgbmatrix import graphics
import config as cfg
import utils
import data

# --- VARIÁVEIS GLOBAIS DE SCROLL ---
scroll_file_x = 64
last_file_scroll_time = time.time()
scroll_msg_x = 64
last_msg_scroll_time = time.time()

# --- FUNÇÕES AUXILIARES ---
def draw_scrolling_text(canv, font, x, y, color, text, last_time):
    """Desenha texto rolando e retorna nova posição X e tempo"""
    text_width = sum(font.CharacterWidth(ord(c)) for c in text)
    graphics.DrawText(canv, font, int(x), y, color, text)
    
    if time.time() - last_time > 0.05:
        x -= 1
        last_time = time.time()
    
    if x + text_width < 0:
        x = 64
        
    return x, last_time

def draw_dynamic_header(canv, text, color):
    """Desenha o cabeçalho com fundo e texto centralizado"""
    for y in range(9): 
        graphics.DrawLine(canv, 0, y, 63, y, cfg.C_BG_HEADER)
    graphics.DrawLine(canv, 0, 8, 63, 8, cfg.C_DIM)
    utils.draw_center(canv, cfg.font_s, 6, color, text)

def format_time(seconds):
    """Formata segundos em HH:MM ou MM:SS"""
    try:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0: return f"{h}h{m}m"
        return f"{m}m{s}s"
    except: return "--:--"

# --- ÍCONES MINIMALISTAS ---
def draw_icon_temp(canv, x, y, color):
    # Termômetro simples
    graphics.DrawLine(canv, x+1, y, x+1, y+3, color)
    graphics.DrawLine(canv, x, y+4, x+2, y+4, color)

def draw_icon_bed(canv, x, y, color):
    # Cama simples
    graphics.DrawLine(canv, x, y+3, x+5, y+3, color)
    graphics.DrawLine(canv, x+1, y+1, x+1, y+2, cfg.C_DIM)
    graphics.DrawLine(canv, x+3, y+1, x+3, y+2, cfg.C_DIM)
    graphics.DrawLine(canv, x+4, y+1, x+4, y+2, cfg.C_DIM)

def draw_icon_clock(canv, x, y, color):
    # Relógio simples
    graphics.DrawCircle(canv, x+2, y+2, 2, color)
    graphics.DrawLine(canv, x+2, y+2, x+2, y+2, color)
    graphics.DrawLine(canv, x+2, y+1, x+2, y+1, color)
    graphics.DrawLine(canv, x+3, y+2, x+3, y+2, color)

def draw_icon_fan(canv, x, y, color):
    # Ícone de ventoinha (cruz)
    graphics.DrawLine(canv, x+2, y, x+2, y+4, color)
    graphics.DrawLine(canv, x, y+2, x+4, y+2, color)

# --- FUNÇÃO PRINCIPAL ---
def draw(canv):
    global scroll_file_x, last_file_scroll_time
    global scroll_msg_x, last_msg_scroll_time

    p = data.dados['printer']
    state = str(p.get('state', 'OFFLINE')).upper()
    printer_name = data.dados.get('printer_name', 'VORON')
    
    # Sensores e Flags
    sensors = p.get('sensors', {})
    is_homed = "x" in p.get('homed_axes', '') and "y" in p.get('homed_axes', '') and "z" in p.get('homed_axes', '')
    is_qgl = p.get('qgl_applied', False)
    
    # Status simplificado
    is_homing = state == "HOMING" or "homing" in p.get('message', '').lower()
    is_leveling = "leveling" in p.get('message', '').lower() or "calibrating" in p.get('message', '').lower()
    is_heating = "HEATING" in state or (p['ext_target'] > 0 and p['ext_actual'] < p['ext_target'] - 2)

    msg = p.get('message', '')
    err_msg = ""
    if state == "ERROR": err_msg = "ERRO: " + msg
    elif state == "OFFLINE": err_msg = "OFFLINE"

    # --- 1. MODO IMPRESSÃO / PAUSA ---
    if state == "PRINTING" or state == "PAUSED":
        # --- LAYOUT ESTILO DASHBOARD (BTC) ---
        
        # 1. CABEÇALHO: Status e Tempo
        # "PRT" (Printing) ou "PAUS" (Paused) - Estilo Ticker BTC
        lbl = "PAUS" if state == "PAUSED" else "PRT"
        col_lbl = cfg.C_YELLOW if state == "PAUSED" else cfg.C_ORANGE
        utils.draw_bold(canv, cfg.font_m, 1, 8, col_lbl, lbl)
        
        # Tempo Restante (Direita)
        remaining = p['total_duration'] - p['print_duration']
        rem_txt = format_time(remaining)
        w_rem = sum(cfg.font_s.CharacterWidth(ord(c)) for c in rem_txt)
        graphics.DrawText(canv, cfg.font_s, 64 - w_rem, 8, cfg.C_WHITE, rem_txt)
        
        # 2. HERO: Porcentagem (Centro - Gigante)
        prog_txt = f"{p['progress']:.0f}%"
        w_prog = sum(cfg.font_l.CharacterWidth(ord(c)) for c in prog_txt)
        # Ajuste para centralizar (draw_bold ocupa +1px)
        x_prog = (64 - w_prog) // 2
        utils.draw_bold(canv, cfg.font_l, x_prog, 22, cfg.C_WHITE, prog_txt)
        
        # 3. SUB-HERO: Z-Height (Abaixo da %)
        z_txt = f"Z: {p['z_height']:.2f}mm"
        utils.draw_center(canv, cfg.font_s, 30, cfg.C_TEAL, z_txt)
        
        # 4. SEPARADOR + BARRA DE PROGRESSO
        graphics.DrawLine(canv, 0, 34, 63, 34, cfg.C_GREY)
        bar_w = int(64 * (p['progress'] / 100.0))
        if bar_w > 0: graphics.DrawLine(canv, 0, 34, bar_w, 34, cfg.C_GREEN)
        
        # 5. DADOS INFERIORES (Grid Limpo)
        # Linha 1: Temperaturas (y=42)
        y_r1 = 42
        draw_icon_temp(canv, 1, y_r1-4, cfg.C_RED)
        graphics.DrawText(canv, cfg.font_s, 7, y_r1, cfg.C_WHITE, f"{p['ext_actual']:.0f}")
        if p['ext_target'] > 0:
            graphics.DrawText(canv, cfg.font_s, 20, y_r1, cfg.C_DIM, f"/{p['ext_target']:.0f}")
            
        draw_icon_bed(canv, 38, y_r1-4, cfg.C_BLUE)
        graphics.DrawText(canv, cfg.font_s, 44, y_r1, cfg.C_WHITE, f"{p['bed_actual']:.0f}")
        
        # Linha 2: Fan e Speed (y=51)
        y_r2 = 51
        draw_icon_fan(canv, 1, y_r2-4, cfg.C_GREY)
        graphics.DrawText(canv, cfg.font_s, 7, y_r2, cfg.C_WHITE, f"{p['fan_speed']}%")
        
        spd = f"{p['print_speed']}mm/s"
        w_spd = sum(cfg.font_s.CharacterWidth(ord(c)) for c in spd)
        graphics.DrawText(canv, cfg.font_s, 64 - w_spd, y_r2, cfg.C_DIM, spd)
        
        # Linha 3: Arquivo (Scrolling) (y=60)
        fname = p['filename'].replace(".gcode", "")
        y_file = 60
        fname_w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in fname)
        if fname_w <= 64:
            utils.draw_center(canv, cfg.font_s, y_file, cfg.C_TEAL, fname)
        else:
            scroll_file_x, last_file_scroll_time = draw_scrolling_text(canv, cfg.font_s, scroll_file_x, y_file, cfg.C_TEAL, fname, last_file_scroll_time)
            
        return

    # --- 2. MODO CONCLUÍDO ---
    if state == "COMPLETE":
        utils.draw_center(canv, cfg.font_l, 25, cfg.C_GREEN, "SUCESSO")
        utils.draw_center(canv, cfg.font_s, 40, cfg.C_WHITE, format_time(p['print_duration']))
        return

    # --- 3. MODO ERRO / OFFLINE ---
    if state == "ERROR" or state == "OFFLINE":
        utils.draw_center(canv, cfg.font_m, 20, cfg.C_RED, err_msg)
        if state == "OFFLINE":
             utils.draw_center(canv, cfg.font_s, 40, cfg.C_DIM, "Conectando...")
        return

    # --- 4. MODO STANDBY / ATIVO ---
    
    # Determinar Texto de Status
    if is_homing: st, col = "HOMING", cfg.C_ORANGE
    elif is_leveling: st, col = "LEVELING", cfg.C_ORANGE
    elif is_heating: st, col = "AQUECENDO", cfg.C_RED
    else: st, col = "PRONTA", cfg.C_GREEN
    
    # Desenhar Header
    draw_dynamic_header(canv, printer_name, cfg.C_TEAL)

    # Status Principal (Grande e Centralizado)
    utils.draw_center(canv, cfg.font_s, 16, col, st)
    graphics.DrawLine(canv, 10, 19, 53, 19, cfg.C_DIM)

    # --- GRID DE SENSORES (Organizado) ---
    y_start = 28
    row_h = 11
    
    # Linha 1: Extrusora e Mesa (Destaque)
    draw_icon_temp(canv, 2, y_start-4, cfg.C_RED)
    graphics.DrawText(canv, cfg.font_s, 9, y_start, cfg.C_WHITE, f"{p['ext_actual']:.0f}")
    
    draw_icon_bed(canv, 34, y_start-4, cfg.C_BLUE)
    graphics.DrawText(canv, cfg.font_s, 41, y_start, cfg.C_WHITE, f"{p['bed_actual']:.0f}")
    
    # Linha 2: Chamber e Eletrônica (Secundários)
    y_r2 = y_start + row_h
    
    temp_chm = sensors.get('CHAMBER', 0)
    graphics.DrawText(canv, cfg.font_s, 2, y_r2, cfg.C_ORANGE, "CH")
    graphics.DrawText(canv, cfg.font_s, 16, y_r2, cfg.C_DIM, f"{temp_chm:.0f}")
    
    temp_pi = sensors.get('RASPIBERRY_4', sensors.get('RPI', 0))
    graphics.DrawText(canv, cfg.font_s, 34, y_r2, cfg.C_GREEN, "PI")
    graphics.DrawText(canv, cfg.font_s, 48, y_r2, cfg.C_DIM, f"{temp_pi:.0f}")

    # Linha 3: Status Flags
    y_r3 = y_r2 + row_h
    
    col_home = cfg.C_WHITE if is_homed else cfg.C_DIM
    graphics.DrawText(canv, cfg.font_s, 2, y_r3, col_home, "HOME")
    
    col_qgl = cfg.C_WHITE if is_qgl else cfg.C_DIM
    graphics.DrawText(canv, cfg.font_s, 34, y_r3, col_qgl, "QGL")

    # Mensagem de Rodapé (se houver e não for redundante)
    if msg and not (is_homing or is_leveling or is_heating):
        y_msg = 62
        msg_w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in msg)
        if msg_w <= 64:
            utils.draw_center(canv, cfg.font_s, y_msg, cfg.C_YELLOW, msg)
        else:
            scroll_msg_x, last_msg_scroll_time = draw_scrolling_text(canv, cfg.font_s, scroll_msg_x, y_msg, cfg.C_YELLOW, msg, last_msg_scroll_time)
