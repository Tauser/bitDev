import time
from rgbmatrix import graphics
import config as cfg
import utils
import data

class PrinterPage:
    def __init__(self):
        # Estado do Scroll
        self.scroll_x = 64
        self.last_scroll = time.time()
        self.scroll_msg_x = 64
        self.last_msg_scroll = time.time()

    def draw(self, canv):
        p = data.dados['printer']
        state = str(p.get('state', 'OFFLINE')).upper()
        
        if state in ['PRINTING', 'PAUSED']:
            self._draw_printing(canv, p, state)
        elif state == 'COMPLETE':
            self._draw_simple_msg(canv, "SUCESSO", cfg.C_GREEN, self._fmt_time(p.get('print_duration', 0)))
        elif state in ['ERROR', 'OFFLINE']:
            msg = "OFFLINE" if state == 'OFFLINE' else f"ERRO: {p.get('message', '')}"
            sub = "Conectando..." if state == 'OFFLINE' else ""
            self._draw_simple_msg(canv, msg, cfg.C_RED, sub)
        else:
            self._draw_standby(canv, p)

    def _draw_printing(self, canv, p, state):
        # 1. HEADER: Status | Porcentagem
        status_txt = "PRINTING" if state == "PRINTING" else "PAUSED"
        col_lbl = cfg.C_ORANGE if state == "PRINTING" else cfg.C_YELLOW
        graphics.DrawText(canv, cfg.font_s, 1, 6, col_lbl, status_txt)
        
        pct_txt = f"{p.get('progress', 0):.0f}%"
        w_pct = sum(cfg.font_s.CharacterWidth(ord(c)) for c in pct_txt)
        graphics.DrawText(canv, cfg.font_s, 64 - w_pct, 6, cfg.C_WHITE, pct_txt)

        # 2. BARRA DE PROGRESSO (Mais larga - 3px)
        graphics.DrawLine(canv, 0, 8, 63, 8, cfg.C_GREY)
        graphics.DrawLine(canv, 0, 9, 63, 9, cfg.C_GREY)
        graphics.DrawLine(canv, 0, 10, 63, 10, cfg.C_GREY)
        
        bar_w = int(64 * (p.get('progress', 0) / 100.0))
        if bar_w > 0:
            graphics.DrawLine(canv, 0, 8, bar_w, 8, cfg.C_GREEN)
            graphics.DrawLine(canv, 0, 9, bar_w, 9, cfg.C_GREEN)
            graphics.DrawLine(canv, 0, 10, bar_w, 10, cfg.C_GREEN)

        # 3. TEMPOS
        # Volta a usar o tempo total original do arquivo (mais estável)
        elapsed = self._fmt_time(p.get('print_duration', 0))
        remaining = self._fmt_time(max(0, p.get('total_duration', 0) - p.get('print_duration', 0)))
        utils.draw_center(canv, cfg.font_s, 18, cfg.C_TEAL, f"{elapsed} / {remaining}")

        # 4. DADOS (Sem ícones, com nomes, sem target)
        # Linha 1: EXT e BED
        y_row1 = 28
        graphics.DrawText(canv, cfg.font_s, 1, y_row1, cfg.C_RED, "EXT")
        graphics.DrawText(canv, cfg.font_s, 15, y_row1, cfg.C_WHITE, f"{p['ext_actual']:.0f}")
        
        graphics.DrawText(canv, cfg.font_s, 32, y_row1, cfg.C_BLUE, "BED")
        graphics.DrawText(canv, cfg.font_s, 46, y_row1, cfg.C_WHITE, f"{p['bed_actual']:.0f}")

        # Linha 2: FAN, LAYER, Z
        y_row2 = 38
        # Usa fonte Tiny (font_t) nos labels para ganhar espaço para os números
        graphics.DrawText(canv, cfg.font_t, 1, y_row2, cfg.C_GREY, "F")
        graphics.DrawText(canv, cfg.font_s, 5, y_row2, cfg.C_WHITE, f"{p.get('fan_speed', 0)}")
        
        graphics.DrawText(canv, cfg.font_t, 20, y_row2, cfg.C_ORANGE, "L")
        graphics.DrawText(canv, cfg.font_s, 24, y_row2, cfg.C_WHITE, f"{p.get('layer', 0)}")
        
        graphics.DrawText(canv, cfg.font_t, 39, y_row2, cfg.C_TEAL, "Z")
        graphics.DrawText(canv, cfg.font_s, 43, y_row2, cfg.C_WHITE, f"{p.get('z_height', 0):.1f}")

        # 5. Arquivo (Scrolling)
        fname = p.get('filename', '').replace(".gcode", "")
        self._draw_scrolling(canv, 48, fname, cfg.C_YELLOW, 'file')

    def _draw_standby(self, canv, p):
        # Header
        for y in range(9): graphics.DrawLine(canv, 0, y, 63, y, cfg.C_BG_HEADER)
        utils.draw_center(canv, cfg.font_s, 6, cfg.C_TEAL, data.dados.get('printer_name', 'VORON'))
        graphics.DrawLine(canv, 0, 9, 63, 9, cfg.C_DIM)

        # Status
        msg = p.get('message', '').lower()
        if "homing" in msg: st, col = "HOMING", cfg.C_ORANGE
        elif "leveling" in msg: st, col = "LEVELING", cfg.C_ORANGE
        elif p['ext_target'] > 0: st, col = "AQUECENDO", cfg.C_RED
        else: st, col = "PRONTA", cfg.C_GREEN
        
        utils.draw_center(canv, cfg.font_m, 20, col, st)

        # Temps Grid
        y_temps = 32
        self._draw_stats_row(canv, y_temps, p['ext_actual'], 0, p['bed_actual'], cfg.C_RED, cfg.C_BLUE)

        # Info Extra (IP ou Msg)
        if p.get('message') and st == "PRONTA":
             self._draw_scrolling(canv, 45, p['message'], cfg.C_YELLOW, 'msg')
        else:
             # Mostra IP se não tiver msg
             ip = data.dados.get('printer_ip', '')
             utils.draw_center(canv, cfg.font_t, 45, cfg.C_DIM, ip)

    # --- Helpers ---
    def _draw_simple_msg(self, canv, title, color, sub=""):
        utils.draw_center(canv, cfg.font_l if not sub else cfg.font_m, 25, color, title)
        if sub: utils.draw_center(canv, cfg.font_s, 40, cfg.C_WHITE, sub)

    def _draw_stats_row(self, canv, y, t1, t1_target, t2, c1, c2):
        self._draw_icon(canv, 2, y-4, c1, 'temp')
        graphics.DrawText(canv, cfg.font_s, 9, y, cfg.C_WHITE, f"{t1:.0f}")
        if t1_target > 0:
            graphics.DrawText(canv, cfg.font_s, 22, y, cfg.C_DIM, f"/{t1_target:.0f}")
        self._draw_icon(canv, 38, y-4, c2, 'bed')
        graphics.DrawText(canv, cfg.font_s, 45, y, cfg.C_WHITE, f"{t2:.0f}")

    def _draw_scrolling(self, canv, y, text, color, type_key):
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in text)
        if w <= 64:
            utils.draw_center(canv, cfg.font_s, y, color, text)
            return

        x = self.scroll_x if type_key == 'file' else self.scroll_msg_x
        last = self.last_scroll if type_key == 'file' else self.last_msg_scroll
        
        graphics.DrawText(canv, cfg.font_s, int(x), y, color, text)
        
        if time.time() - last > 0.05:
            x -= 1
            last = time.time()
            if x + w < 0: x = 64
            
        if type_key == 'file': self.scroll_x, self.last_scroll = x, last
        else: self.scroll_msg_x, self.last_msg_scroll = x, last

    def _draw_icon(self, canv, x, y, color, name):
        if name == 'temp':
            graphics.DrawLine(canv, x+1, y, x+1, y+3, color)
            graphics.DrawLine(canv, x, y+4, x+2, y+4, color)
        elif name == 'bed':
            graphics.DrawLine(canv, x, y+3, x+5, y+3, color)
            graphics.DrawLine(canv, x+1, y+1, x+1, y+2, cfg.C_DIM)
            graphics.DrawLine(canv, x+3, y+1, x+3, y+2, cfg.C_DIM)
            graphics.DrawLine(canv, x+4, y+1, x+4, y+2, cfg.C_DIM)
        elif name == 'fan':
            graphics.DrawLine(canv, x+2, y, x+2, y+4, color)
            graphics.DrawLine(canv, x, y+2, x+4, y+2, color)

    def _fmt_time(self, s):
        try:
            m, s = divmod(int(s), 60)
            h, m = divmod(m, 60)
            return f"{h}h{m}m" if h > 0 else f"{m}m{s}s"
        except: return "--:--"

# Instância única
printer_page = PrinterPage()

def draw(canv):
    printer_page.draw(canv)
