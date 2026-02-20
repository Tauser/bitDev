import time
import math
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
        
        # --- DEBUG: FORÇAR TELA DE IMPRESSÃO PARA EDIÇÃO ---
        # state = 'PRINTING'
        # # if p['ext_actual'] == 0: # Se não tiver dados reais, usa fictícios
        # if True:
        #     p = p.copy()
        #     p['progress'] = 100
        #     p['print_duration'] = 5430
        #     p['total_duration'] = 8100
        #     p['ext_actual'] = 240
        #     p['bed_actual'] = 100
        #     p['fan_speed'] = 100
        #     p['layer'] = 215
        #     p['total_layers'] = 400
        #     p['speed_factor'] = 100
        #     p['sensors'] = {'chamber': 45} # Simula sensor de câmara
        #     p['z_height'] = 42.5
        #     p['filename'] = "Voron_Cube_ABS.gcode"

        
        if state in ['PRINTING', 'PAUSED']:
            self._draw_printing(canv, p, state)
        elif state == 'COMPLETE':
            self._draw_simple_msg(canv, "CONCLUIDO", cfg.C_GREEN, self._fmt_time(p.get('print_duration', 0)))
        elif state in ['ERROR', 'OFFLINE']:
            msg = "OFFLINE" if state == 'OFFLINE' else f"ERRO: {p.get('message', '')}"
            sub = "Conectando..." if state == 'OFFLINE' else ""
            self._draw_simple_msg(canv, msg, cfg.C_ORANGE, sub)
        else:
            self._draw_standby(canv, p)

    def _draw_printing(self, canv, p, state):
        # 1. HEADER: Status | Porcentagem
        status_txt = "IMPRIMINDO" if state == "PRINTING" else "PAUSADO"
        col_lbl = cfg.C_ORANGE if state == "PRINTING" else cfg.C_YELLOW
        col_lbl = cfg.C_WHITE if state == "PRINTING" else cfg.C_YELLOW
        utils.draw_center(canv, cfg.font_s, 6, col_lbl, status_txt)
        
        # Separador do Header
        graphics.DrawLine(canv, 0, 8, 63, 8, cfg.C_GREY)

        progress = p.get('progress', 0)
        
        # Alternância (5s Dados / 5s Progresso Circular)
        show_circle = int(time.time() / 5) % 2 == 0
        
        if show_circle:
            # --- MODO 1: PROGRESSO CIRCULAR ---
            cx, cy = 32, 23
            radius = 13
            
            # Cor baseada no progresso (Cores frias/alegres)
            if progress < 30: bar_col = cfg.C_BLUE
            elif progress < 70: bar_col = cfg.C_TEAL
            else: bar_col = cfg.C_GREEN
            
            # Efeito de Sucesso (100%) - Pulso Suave (Verde <-> Branco)
            if progress >= 99:
                val = int((math.sin(time.time() * 5) + 1) * 127.5) # Oscila 0-255
                bar_col = graphics.Color(val, 255, val)

            # Desenha círculo de fundo (dim)
            for angle in range(0, 360, 15):
                rad = math.radians(angle)
                x = int(cx + radius * math.cos(rad))
                y = int(cy + radius * math.sin(rad))
                canv.SetPixel(x, y, 50, 50, 50)

            # Desenha arco de progresso
            end_angle = int(360 * (progress / 100.0))
            for angle in range(-90, -90 + end_angle):
                rad = math.radians(angle)
                x = int(cx + radius * math.cos(rad))
                y = int(cy + radius * math.sin(rad))
                canv.SetPixel(x, y, bar_col.red, bar_col.green, bar_col.blue)
                
                # Espessura interna
                x2 = int(cx + (radius-1) * math.cos(rad))
                y2 = int(cy + (radius-1) * math.sin(rad))
                canv.SetPixel(x2, y2, bar_col.red, bar_col.green, bar_col.blue)

            # Texto no centro
            pct_txt = f"{progress:.0f}%"
            w_pct = sum(cfg.font_m.CharacterWidth(ord(c)) for c in pct_txt)
            graphics.DrawText(canv, cfg.font_m, cx - (w_pct // 2), cy + 4, cfg.C_WHITE, pct_txt)
            
        else:
            # --- MODO 2: DADOS (Temperaturas e Status) ---
            graphics.DrawLine(canv, 32, 12, 32, 36, cfg.C_GREY) # Divisória Vertical
            
            y = 18
            step = 8
            
            # LINHA 1: EXT | Z
            graphics.DrawText(canv, cfg.font_s, 2, y, cfg.C_TEAL, "EXT")
            val = f"{p['ext_actual']:.0f}°"
            w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
            graphics.DrawText(canv, cfg.font_s, 31-w, y, cfg.C_WHITE, val)
            
            graphics.DrawText(canv, cfg.font_t, 34, y, cfg.C_WHITE, "Z")
            val = f"{p.get('z_height', 0):.1f}"
            w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
            graphics.DrawText(canv, cfg.font_s, 62-w, y, cfg.C_WHITE, val)
            
            # LINHA 2: BED | SPD
            y += step
            graphics.DrawText(canv, cfg.font_s, 2, y, cfg.C_TEAL, "BED")
            val = f"{p['bed_actual']:.0f}°"
            w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
            graphics.DrawText(canv, cfg.font_s, 31-w, y, cfg.C_WHITE, val)

            graphics.DrawText(canv, cfg.font_s, 34, y, cfg.C_TEAL, "SPD")
            val = f"{p.get('speed_factor', 100)}%"
            w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
            graphics.DrawText(canv, cfg.font_s, 62-w, y, cfg.C_WHITE, val)

            # LINHA 3: CH | FAN
            y += step
            chamber_temp = 0
            for k, v in p.get('sensors', {}).items():
                if 'chamber' in k.lower() or 'enclosure' in k.lower(): chamber_temp = v; break
            
            graphics.DrawText(canv, cfg.font_s, 2, y, cfg.C_TEAL, "CH")
            val = f"{chamber_temp:.0f}°" if chamber_temp > 0 else "--"
            w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
            graphics.DrawText(canv, cfg.font_s, 31-w, y, cfg.C_WHITE, val)

            # FAN
            graphics.DrawText(canv, cfg.font_s, 34, y, cfg.C_TEAL, "FAN")
            val = f"{p.get('fan_speed', 0)}%"
            w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
            graphics.DrawText(canv, cfg.font_s, 62-w, y, cfg.C_WHITE, val)

        # Divisória Horizontal (Sempre visível para separar Layer/Timers)
        graphics.DrawLine(canv, 0, 38, 63, 38, cfg.C_GREY)

        # 5. LAYER (Split Colors)
        y = 45
        cur_l = p.get('layer', 0)
        tot_l = p.get('total_layers', 0)
        
        txt_lbl = "LYR "
        txt_cur = f"{cur_l}"
        txt_tot = f"/{tot_l}"
        
        w_lbl = sum(cfg.font_s.CharacterWidth(ord(c)) for c in txt_lbl)
        w_cur = sum(cfg.font_s.CharacterWidth(ord(c)) for c in txt_cur)
        w_tot = sum(cfg.font_s.CharacterWidth(ord(c)) for c in txt_tot)
        
        total_w = w_lbl + w_cur + w_tot
        start_x = (64 - total_w) // 2
        
        graphics.DrawText(canv, cfg.font_s, start_x, y, cfg.C_WHITE, txt_lbl + txt_cur)
        graphics.DrawText(canv, cfg.font_s, start_x + w_lbl + w_cur, y, cfg.C_YELLOW, txt_tot)

        # 6. TIMERS (One per line)
        elapsed = self._fmt_time(p.get('print_duration', 0))
        rem_sec = max(0, p.get('total_duration', 0) - p.get('print_duration', 0))
        remaining = self._fmt_time(rem_sec)
        
        # Elapsed
        y = 53
        ic_x, ic_y = 2, y - 3
        # Clock Icon
        graphics.DrawLine(canv, ic_x+1, ic_y-2, ic_x+3, ic_y-2, cfg.C_WHITE)
        graphics.DrawLine(canv, ic_x+1, ic_y+2, ic_x+3, ic_y+2, cfg.C_WHITE)
        graphics.DrawLine(canv, ic_x, ic_y-1, ic_x, ic_y+1, cfg.C_WHITE)
        graphics.DrawLine(canv, ic_x+4, ic_y-1, ic_x+4, ic_y+1, cfg.C_WHITE)
        canv.SetPixel(ic_x+2, ic_y, 255, 255, 255)
        # Static Hand
        canv.SetPixel(ic_x+3, ic_y, 255, 255, 255)
        canv.SetPixel(ic_x+2, ic_y-1, 255, 255, 255) # Segundo ponteiro
        
        graphics.DrawText(canv, cfg.font_s, 12, y, cfg.C_TEAL, elapsed)
        
        # Remaining
        y = 61
        ic_x, ic_y = 2, y - 3
        # Hourglass Icon
        graphics.DrawLine(canv, ic_x, ic_y-2, ic_x+4, ic_y-2, cfg.C_WHITE)
        graphics.DrawLine(canv, ic_x, ic_y+2, ic_x+4, ic_y+2, cfg.C_WHITE)
        graphics.DrawLine(canv, ic_x, ic_y-2, ic_x+2, ic_y, cfg.C_WHITE)
        graphics.DrawLine(canv, ic_x+4, ic_y-2, ic_x+2, ic_y, cfg.C_WHITE)
        graphics.DrawLine(canv, ic_x, ic_y+2, ic_x+2, ic_y, cfg.C_WHITE)
        graphics.DrawLine(canv, ic_x+4, ic_y+2, ic_x+2, ic_y, cfg.C_WHITE)
        
        # Alterna entre Restante e ETA a cada 4s
        if int(time.time() / 4) % 2 == 0:
            graphics.DrawText(canv, cfg.font_s, 12, y, cfg.C_YELLOW, remaining)
        else:
            eta = time.localtime(time.time() + rem_sec)
            graphics.DrawText(canv, cfg.font_s, 12, y, cfg.C_YELLOW, time.strftime("ETA %H:%M", eta))

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
            st, col = "STANDBY", cfg.C_GREEN
        
        # Status Title
        utils.draw_center(canv, cfg.font_s, 6, col, st)
        graphics.DrawLine(canv, 0, 8, 63, 8, cfg.C_GREY)

        self._draw_idle_status(canv, p)

    def _draw_idle_status(self, canv, p):
        # Divisória Vertical
        graphics.DrawLine(canv, 32, 9, 32, 35, cfg.C_GREY)
        # Divisória Horizontal
        graphics.DrawLine(canv, 0, 35, 63, 35, cfg.C_GREY)

        # --- Lado Esquerdo: Térmica (x 0-31) ---
        y = 16
        step = 8

        # 1. EXT
        graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_TEAL, "EXT")
        val = f"{p['ext_actual']:.0f}°"
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
        graphics.DrawText(canv, cfg.font_s, 31-w, y, cfg.C_WHITE, val)

        # 2. BED
        y += step
        graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_TEAL, "BED")
        val = f"{p['bed_actual']:.0f}°"
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
        graphics.DrawText(canv, cfg.font_s, 31-w, y, cfg.C_WHITE, val)

        # 3. FAN
        y += step
        graphics.DrawText(canv, cfg.font_s, 1, y, cfg.C_TEAL, "FAN")
        val = f"{p.get('fan_speed', 0)}%"
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
        graphics.DrawText(canv, cfg.font_s, 31-w, y, cfg.C_WHITE, val)

        # --- Lado Direito: Movimento (x 33-63) ---
        y = 16
        
        # 1. HOME
        # Icone Home (Animado)
        ic_x, ic_y = 34, y - 3
        graphics.DrawLine(canv, ic_x+2, ic_y-2, ic_x, ic_y, cfg.C_TEAL)   # Roof L
        graphics.DrawLine(canv, ic_x+2, ic_y-2, ic_x+4, ic_y, cfg.C_TEAL) # Roof R
        graphics.DrawLine(canv, ic_x, ic_y, ic_x, ic_y+3, cfg.C_TEAL)     # Wall L
        graphics.DrawLine(canv, ic_x+4, ic_y, ic_x+4, ic_y+3, cfg.C_TEAL) # Wall R
        graphics.DrawLine(canv, ic_x, ic_y+3, ic_x+4, ic_y+3, cfg.C_TEAL) # Floor
        # Porta estática (Fechada)
        canv.SetPixel(ic_x+2, ic_y+3, cfg.C_TEAL.red, cfg.C_TEAL.green, cfg.C_TEAL.blue)

        # Janela (Acende à noite: 18h-06h)
        hour = time.localtime().tm_hour
        is_night = hour >= 18 or hour < 6
        if is_night:
            canv.SetPixel(ic_x+1, ic_y+1, 255, 255, 0)

        # Sol / Lua (Céu)
        sky_x, sky_y = ic_x + 8, ic_y - 4
        if not is_night:
            # Sol (Dia)
            canv.SetPixel(sky_x, sky_y, 255, 255, 0)
            canv.SetPixel(sky_x+1, sky_y, 255, 255, 0)
            canv.SetPixel(sky_x, sky_y+1, 255, 255, 0)
            canv.SetPixel(sky_x+1, sky_y+1, 255, 255, 0)
            if int(time.time()) % 2 == 0: # Brilho
                canv.SetPixel(sky_x-1, sky_y, 255, 255, 0); canv.SetPixel(sky_x+2, sky_y, 255, 255, 0)
                canv.SetPixel(sky_x, sky_y-1, 255, 255, 0); canv.SetPixel(sky_x, sky_y+2, 255, 255, 0)
        else:
            # Lua (Noite)
            canv.SetPixel(sky_x+1, sky_y, 200, 200, 200)
            canv.SetPixel(sky_x, sky_y+1, 200, 200, 200)
            canv.SetPixel(sky_x+1, sky_y+2, 200, 200, 200)

        # Fumaça (Se aquecendo)
        if p.get('ext_target', 0) > 0 or p.get('bed_target', 0) > 0:
            s_tick = int(time.time() * 5) % 4
            sx, sy = ic_x + 2, ic_y - 3
            
            if s_tick == 0:
                canv.SetPixel(sx, sy, 180, 180, 180)
            elif s_tick == 1:
                canv.SetPixel(sx, sy-1, 180, 180, 180)
                canv.SetPixel(sx+1, sy-2, 120, 120, 120)
            elif s_tick == 2:
                canv.SetPixel(sx+1, sy-2, 120, 120, 120)
                canv.SetPixel(sx+2, sy-3, 80, 80, 80)
            elif s_tick == 3:
                canv.SetPixel(sx+2, sy-3, 60, 60, 60)
        else:
            # Zzz (Dormindo - Ociosa)
            z_tick = int(time.time() * 1.5) % 4
            zx, zy = ic_x + 2, ic_y - 3
            
            if z_tick == 1: # .
                canv.SetPixel(zx, zy, 150, 150, 255)
            elif z_tick == 2: # z
                canv.SetPixel(zx+1, zy-1, 150, 150, 255); canv.SetPixel(zx+2, zy-1, 150, 150, 255)
                canv.SetPixel(zx+1, zy, 150, 150, 255); canv.SetPixel(zx+2, zy, 150, 150, 255)
            elif z_tick == 3: # Z
                graphics.DrawLine(canv, zx+2, zy-3, zx+4, zy-3, cfg.C_TEAL)
                canv.SetPixel(zx+3, zy-2, cfg.C_TEAL.red, cfg.C_TEAL.green, cfg.C_TEAL.blue)
                graphics.DrawLine(canv, zx+2, zy-1, zx+4, zy-1, cfg.C_TEAL)

        homed = p.get('homed_axes', '').upper()
        if not homed: homed = "NO"
        col = cfg.C_GREEN if homed == "XYZ" else cfg.C_BLUE
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in homed)
        graphics.DrawText(canv, cfg.font_s, 63-w, y, col, homed)

        # 2. QGL
        y += step
        graphics.DrawText(canv, cfg.font_t, 34, y, cfg.C_TEAL, "QGL")
        qgl = p.get('qgl_applied', False)
        val = "OK" if qgl else "NO"
        col = cfg.C_GREEN if qgl else cfg.C_RED
        w = sum(cfg.font_s.CharacterWidth(ord(c)) for c in val)
        graphics.DrawText(canv, cfg.font_s, 63-w, y, col, val)

        # 3. Z-POS
        y += step
        graphics.DrawText(canv, cfg.font_t, 34, y, cfg.C_TEAL, "Z")
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
        val = f"{hours}h"
        graphics.DrawText(canv, cfg.font_s, 10, y, cfg.C_WHITE, val)

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
        val = f"{meters}m"
        graphics.DrawText(canv, cfg.font_s, 10, y, cfg.C_WHITE, val)

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
            return f"{h:02d}:{m:02d}:{s:02d}"
        except: return "--:--"

# Instância única
printer_page = PrinterPage()

def draw(canv):
    printer_page.draw(canv)
