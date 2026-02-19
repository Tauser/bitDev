import time
import os
from PIL import Image, ImageEnhance
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
        self.bg_image = None
        try:
            img_path = os.path.join(cfg.BASE_DIR, 'images', 'voron_logo.png')
            if os.path.exists(img_path):
                img = Image.open(img_path).convert('RGB').resize((64, 64))
                enhancer = ImageEnhance.Brightness(img)
                self.bg_image = enhancer.enhance(0.1)
        except: pass

    def draw(self, canv):
        if self.bg_image:
            canv.SetImage(self.bg_image, 0, 0)

        p = data.dados['printer']
        state = str(p.get('state', 'OFFLINE')).upper()
        
        if state in ['PRINTING', 'PAUSED']:
            self._draw_printing(canv, p, state)
        elif state == 'COMPLETE':
            self._draw_simple_msg(canv, "SUCESSO", cfg.C_GREEN, self._fmt_time(p.get('print_duration', 0)))
        elif state in ['ERROR', 'OFFLINE']:
            msg = "OFFLINE" if state == 'OFFLINE' else f"ERRO: {p.get('message', '')}"
            sub = "Conectando..." if state == 'OFFLINE' else ""
            self._draw_simple_msg(canv, msg, cfg.C_ORANGE, sub)
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
        graphics.DrawText(canv, cfg.font_s, 1, y_row1, cfg.C_ORANGE, "EXT")
        graphics.DrawText(canv, cfg.font_s, 15, y_row1, cfg.C_WHITE, f"{p['ext_actual']:.0f}")
        
        graphics.DrawText(canv, cfg.font_s, 32, y_row1, cfg.C_ORANGE, "BED")
        graphics.DrawText(canv, cfg.font_s, 46, y_row1, cfg.C_WHITE, f"{p['bed_actual']:.0f}")

        # Linha 2: FAN, LAYER, Z
        y_row2 = 36
        # Usa fonte Tiny (font_t) nos labels para ganhar espaço para os números
        graphics.DrawText(canv, cfg.font_t, 1, y_row2, cfg.C_ORANGE, "FAN")
        graphics.DrawText(canv, cfg.font_s, 5, y_row2, cfg.C_WHITE, f"{p.get('fan_speed', 0)}")
        
        graphics.DrawText(canv, cfg.font_t, 20, y_row2, cfg.C_ORANGE, "L")
        graphics.DrawText(canv, cfg.font_s, 24, y_row2, cfg.C_WHITE, f"{p.get('layer', 0)}")
        
        graphics.DrawText(canv, cfg.font_t, 39, y_row2, cfg.C_WHITE, "Z")
        graphics.DrawText(canv, cfg.font_s, 43, y_row2, cfg.C_WHITE, f"{p.get('z_height', 0):.1f}")

        # 5. Arquivo (Scrolling)
        fname = p.get('filename', '').replace(".gcode", "")
        self._draw_scrolling(canv, 48, fname, cfg.C_YELLOW, 'file')

    def _draw_standby(self, canv, p):
        # Detect Status
        msg = p.get('message', '').lower()
        is_heating = (p['ext_target'] > 0 or p['bed_target'] > 0)
        
        if "homing" in msg: 
            st, col = "HOMING", cfg.C_ORANGE
        elif "leveling" in msg or "calibrating" in msg: 
            st, col = "LEVELING", cfg.C_ORANGE
        elif is_heating: 
            st, col = "AQUECENDO", cfg.C_YELLOW
        else: 
            st, col = "PRONTA", cfg.C_GREEN
        
        # Status Title
        utils.draw_center(canv, cfg.font_s, 6, col, st)
        graphics.DrawLine(canv, 0, 8, 63, 8, cfg.C_GREY)

        if is_heating:
            self._draw_heating_bars(canv, p)
        else:
            self._draw_idle_status(canv, p)

        # Footer (IP)
        ip = data.dados.get('printer_ip', '')
        utils.draw_center(canv, cfg.font_t, 63, cfg.C_DIM, ip)

    def _draw_heating_bars(self, canv, p):
        self._draw_temp_bar(canv, 25, "EXT", p['ext_actual'], p['ext_target'], cfg.C_ORANGE)
        self._draw_temp_bar(canv, 45, "BED", p['bed_actual'], p['bed_target'], cfg.C_WHITE)

    def _draw_temp_bar(self, canv, y, label, curr, target, color):
        graphics.DrawText(canv, cfg.font_t, 0, y, color, label)
        val = f"{curr:.0f}/{target:.0f}"
        w = sum(cfg.font_t.CharacterWidth(ord(c)) for c in val)
        graphics.DrawText(canv, cfg.font_t, 64-w, y, cfg.C_WHITE, val)
        
        graphics.DrawLine(canv, 0, y+2, 63, y+2, cfg.C_GREY)
        if target > 0:
            pct = min(1.0, curr / target)
            bar_w = int(63 * pct)
            if bar_w > 0: graphics.DrawLine(canv, 0, y+2, bar_w, y+2, color)

    def _draw_idle_status(self, canv, p):
        # Divisória Vertical
        graphics.DrawLine(canv, 32, 9, 32, 35, cfg.C_GREY)
        # Divisória Horizontal
        graphics.DrawLine(canv, 0, 35, 63, 35, cfg.C_GREY)

        # --- Lado Esquerdo: Térmica (x 0-31) ---
        y = 16
        step = 8

        # 1. EXT
        graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_ORANGE, "EXT")
        val = f"{p['ext_actual']:.0f}°"
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
        graphics.DrawText(canv, cfg.font_s, 31-w, y, cfg.C_WHITE, val)

        # 2. BED
        y += step
        graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_ORANGE, "BED")
        val = f"{p['bed_actual']:.0f}°"
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
        graphics.DrawText(canv, cfg.font_s, 31-w, y, cfg.C_WHITE, val)

        # 3. FAN
        y += step
        graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_ORANGE, "FAN")
        val = f"{p.get('fan_speed', 0)}%"
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
        graphics.DrawText(canv, cfg.font_s, 31-w, y, cfg.C_WHITE, val)

        # --- Lado Direito: Movimento (x 33-63) ---
        y = 16
        
        # 1. HOME
        graphics.DrawText(canv, cfg.font_t, 34, y, cfg.C_WHITE, "HOME")
        homed = p.get('homed_axes', '').upper()
        if not homed: homed = "NO"
        col = cfg.C_GREEN if homed == "XYZ" else cfg.C_BLUE
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in homed)
        graphics.DrawText(canv, cfg.font_s, 63-w, y, col, homed)

        # 2. QGL
        y += step
        graphics.DrawText(canv, cfg.font_t, 34, y, cfg.C_WHITE, "QGL")
        qgl = p.get('qgl_applied', False)
        val = "OK" if qgl else "NO"
        col = cfg.C_GREEN if qgl else cfg.C_RED
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
        graphics.DrawText(canv, cfg.font_s, 63-w, y, col, val)

        # 3. Z-POS
        y += step
        graphics.DrawText(canv, cfg.font_t, 34, y, cfg.C_WHITE, "Z")
        #y += 8
        z_val = f"{p.get('z_height', 0):.2f}"
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in z_val)
        graphics.DrawText(canv, cfg.font_s, 63-w, y, cfg.C_WHITE, z_val)

        # 4. LIFE (Clock)
        y = 42
        ic_x, ic_y = 2, y - 3
        graphics.DrawLine(canv, ic_x+1, ic_y-2, ic_x+3, ic_y-2, cfg.C_WHITE) # Top
        graphics.DrawLine(canv, ic_x+1, ic_y+2, ic_x+3, ic_y+2, cfg.C_WHITE) # Bot
        graphics.DrawLine(canv, ic_x, ic_y-1, ic_x, ic_y+1, cfg.C_WHITE)     # Left
        graphics.DrawLine(canv, ic_x+4, ic_y-1, ic_x+4, ic_y+1, cfg.C_WHITE) # Right
        canv.SetPixel(ic_x+2, ic_y, 255, 255, 255)   # Center
        
        # Ponteiro Fixo (Hora - 3h)
        canv.SetPixel(ic_x+3, ic_y, 255, 255, 255)

        # Ponteiro Rotativo (Minuto)
        tick = int(time.time() * 2) % 8
        hand_map = [(0,-1), (1,-1), (1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1)]
        dx, dy = hand_map[tick]
        canv.SetPixel(ic_x+2+dx, ic_y+dy, 255, 255, 255)
        
        total_sec = p.get('stats', {}).get('total_time', 0)
        hours = int(total_sec / 3600)
        val = f"{hours} horas"
        graphics.DrawText(canv, cfg.font_s, 10, y, cfg.C_TEAL, val)

        # 5. FIL (Spool)
        y = 50
        ic_x = 2
        graphics.DrawLine(canv, ic_x, y-5, ic_x+4, y-5, cfg.C_WHITE) # Top Plate
        graphics.DrawLine(canv, ic_x, y-1, ic_x+4, y-1, cfg.C_WHITE)     # Bot Plate

        # Animated "unspooling" effect
        tick = int(time.time() * 3) % 4 # Cycle 0, 1, 2, 3
        
        # Base filament
        graphics.DrawLine(canv, ic_x+1, y-4, ic_x+3, y-4, cfg.C_ORANGE)
        graphics.DrawLine(canv, ic_x+1, y-3, ic_x+3, y-3, cfg.C_ORANGE)
        graphics.DrawLine(canv, ic_x+1, y-2, ic_x+3, y-2, cfg.C_ORANGE)
        
        # Animation part (a small tail coming out)
        if tick > 0: canv.SetPixel(ic_x+4, y-3, cfg.C_ORANGE.red, cfg.C_ORANGE.green, cfg.C_ORANGE.blue)
        if tick > 1: canv.SetPixel(ic_x+5, y-3, cfg.C_ORANGE.red, cfg.C_ORANGE.green, cfg.C_ORANGE.blue)
        if tick > 2: canv.SetPixel(ic_x+5, y-2, cfg.C_ORANGE.red, cfg.C_ORANGE.green, cfg.C_ORANGE.blue)
        
        total_mm = p.get('stats', {}).get('total_filament', 0)
        meters = int(total_mm / 1000)
        val = f"{meters} metros"
        graphics.DrawText(canv, cfg.font_s, 10, y, cfg.C_ORANGE, val)

    # --- Helpers ---
    def _draw_simple_msg(self, canv, title, color, sub=""):
        utils.draw_center(canv, cfg.font_l if not sub else cfg.font_m, 25, color, title)
        if sub: utils.draw_center(canv, cfg.font_s, 40, cfg.C_WHITE, sub)

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
