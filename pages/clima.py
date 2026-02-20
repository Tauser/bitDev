from PIL import Image, ImageDraw
from rgbmatrix import graphics
import config as cfg
import utils
import data
import math
import time
import random
import os
import datetime

class WeatherPage:
    def __init__(self):
        self.icons_cache = {}
        self.C_WARM_WHITE = graphics.Color(255, 245, 220)
        self.C_DARK_GREY = graphics.Color(30, 30, 30)
        self.C_LIGHT_GREY = graphics.Color(180, 180, 180)
        
        # Cores (Tuples para PIL)
        self.C_BLUE_DROP = (64, 164, 255)
        self.C_SUN_YELLOW = (255, 215, 0)
        self.C_SUN_ORANGE = (255, 140, 0)
        self.C_CLOUD_WHITE = (220, 220, 220)
        self.C_CLOUD_GREY = (150, 150, 150)
        self.C_CLOUD_DARK = (80, 80, 80)

    def _get_moon_phase(self):
        """Calcula a fase da lua (0-29)"""
        try:
            now = datetime.datetime.now()
            ref = datetime.datetime(2024, 1, 11) # Lua Nova
            days = (now - ref).days
            return days % 30
        except: return 15

    def _get_icon(self, name, size, is_night=False, hour=12, wind_speed=0):
        """Gera ícones animados proceduralmente e detalhados"""
        # Cria imagem RGBA para transparência durante o desenho
        img = Image.new("RGBA", size, (0,0,0,0))
        d = ImageDraw.Draw(img)
        w, h = size
        t = time.time()
        
        # --- Helper para desenhar nuvem com profundidade ---
        def draw_cloud_detailed(cx, cy):
            # Cores
            if is_night:
                c_border = (50, 50, 70)
                c_body   = (100, 110, 130)
                c_shadow = (70, 80, 100)
            else:
                c_border = (70, 130, 200)  # Azul escuro (Borda)
                c_body   = (240, 250, 255) # Azul clarinho (Corpo)
                c_shadow = (190, 220, 240) # Sombra suave (Volume)
            
            # 1. Borda (Silhueta expandida)
            # Base
            d.rectangle((cx+3, cy+6, cx+19, cy+14), fill=c_border)
            # Puffs
            d.ellipse((cx-1, cy+4, cx+9, cy+14), fill=c_border)    # Esq
            d.ellipse((cx+13, cy+4, cx+23, cy+14), fill=c_border)  # Dir
            d.ellipse((cx+5, cy-1, cx+17, cy+11), fill=c_border)   # Topo

            # 2. Corpo (Cor interna - deslocado 1px para dentro)
            d.rectangle((cx+4, cy+7, cx+18, cy+13), fill=c_body)
            d.ellipse((cx, cy+5, cx+8, cy+13), fill=c_body)
            d.ellipse((cx+14, cy+5, cx+22, cy+13), fill=c_body)
            d.ellipse((cx+6, cy, cx+16, cy+10), fill=c_body)
            
            # 3. Volume (Sombra interna na base)
            d.chord((cx+6, cy, cx+16, cy+10), -45, 135, fill=c_shadow) # Sombra no puff central

        # --- ÍCONES GRANDES (24x24) ---
        
        if name == 'sun': 
            cx, cy = w//2, h//2
            if is_night:
                phase = self._get_moon_phase()
                # Lua
                d.ellipse((cx-6, cy-6, cx+6, cy+6), fill=(220, 220, 220))
                # Sombra da fase (Simplificada)
                if 0 <= phase < 4 or phase > 26: # Nova
                    d.ellipse((cx-6, cy-6, cx+6, cy+6), fill=(40, 40, 50), outline=(80, 80, 80))
                elif 4 <= phase < 11: # Crescente
                    d.chord((cx-6, cy-6, cx+6, cy+6), 90, 270, fill=(40, 40, 50))
                elif 18 < phase <= 26: # Minguante
                    d.chord((cx-6, cy-6, cx+6, cy+6), 270, 90, fill=(40, 40, 50))
                
                # Crateras (se visível)
                if 7 < phase < 22:
                    d.ellipse((cx-2, cy-3, cx+1, cy), fill=(180, 180, 180))
                    d.ellipse((cx+2, cy+1, cx+4, cy+3), fill=(180, 180, 180))
            else:
                # Sol com Raios Girando
                for i in range(8):
                    angle = (t * 1.0) + (i * math.pi / 4)
                    r1, r2 = 6, 10
                    x1 = cx + math.cos(angle) * r1
                    y1 = cy + math.sin(angle) * r1
                    x2 = cx + math.cos(angle) * r2
                    y2 = cy + math.sin(angle) * r2
                    d.line((x1, y1, x2, y2), fill=(255, 140, 0), width=2)
                d.ellipse((cx-5, cy-5, cx+5, cy+5), fill=(255, 215, 0))
                d.ellipse((cx-2, cy-2, cx+2, cy+2), fill=(255, 255, 200)) # Brilho central

        elif name == 'partly_cloudy':
            # Sol/Lua atrás
            sx, sy = w//2 + 2, h//2 - 4
            if is_night:
                d.ellipse((sx-4, sy-4, sx+4, sy+4), fill=(200, 200, 200))
            else:
                d.ellipse((sx-5, sy-5, sx+5, sy+5), fill=(255, 215, 0))
                # Raios parciais
                for i in range(8):
                    angle = (t * 1.0) + (i * math.pi / 4)
                    x2 = sx + math.cos(angle) * 9
                    y2 = sy + math.sin(angle) * 9
                    d.line((sx, sy, x2, y2), fill=(255, 140, 0), width=1)

            # Nuvem na frente
            draw_cloud_detailed(1, 7)

        elif name == 'cloud':
            draw_cloud_detailed(1, 4)

        elif name == 'rain' or name == 'storm':
            draw_cloud_detailed(1, 4)
            
            # Gotas caindo
            drop_col = (80, 160, 255)
            
            # Inclinação baseada no vento (0 a 4 pixels)
            slant = int(wind_speed / 8)
            if slant > 4: slant = 4
            
            for i in range(3):
                dx = 6 + i*6
                dy = 19 + int((t * 15 + i*5) % 8) # Baixado para 19 (base da nuvem)
                if dy < h:
                    d.line((dx, dy, dx - slant, dy+2), fill=drop_col)
            
            # Raios (Ocasional para chuva, frequente para tempestade)
            chance = 0.02 if name == 'rain' else 0.2 # 2% chance por frame para chuva comum
            if random.random() < chance:
                lx = random.randint(6, 14)
                ly = 19 # Baixado para sair da base da nuvem
                # Zig-zag do raio
                d.line((lx, ly, lx-2, ly+3), fill=(255, 255, 100), width=1)
                d.line((lx-2, ly+3, lx, ly+3), fill=(255, 255, 100), width=1)
                d.line((lx, ly+3, lx-1, ly+6), fill=(255, 255, 100), width=1)

        # --- ÍCONES PEQUENOS (8x8) ---
        
        elif name == 'humidity': # Gota
            d.ellipse((2, 3, 6, 7), fill=self.C_BLUE_DROP)
            d.polygon([(4, 1), (2, 4), (6, 4)], fill=self.C_BLUE_DROP)
            d.point((3, 4), fill=(255, 255, 255)) # Brilho
            
        elif name == 'wind': # Vento
            # Estático com "voltinhas" (curvas)
            d.line((0, 2, 4, 2), fill=(200, 200, 200)) # Linha cima
            d.point((5, 3), fill=(200, 200, 200))      # Voltinha baixo
            d.line((2, 5, 6, 5), fill=(200, 200, 200)) # Linha baixo
            d.point((7, 4), fill=(200, 200, 200))      # Voltinha cima
            
        elif name == 'pop': # Probabilidade de Chuva (8x8)
            d.ellipse((0, 1, 4, 4), fill=(180, 180, 180)) # Nuvem
            d.ellipse((2, 0, 6, 3), fill=(180, 180, 180))
            d.line((3, 5, 3, 6), fill=self.C_BLUE_DROP)   # Gota
            
        elif name == 'uv': # Sol UV
            d.ellipse((1, 1, 6, 6), outline=(255, 140, 0))
            d.point((3, 3), fill=(255, 200, 0))
            d.point((4, 3), fill=(255, 200, 0))
            d.point((3, 4), fill=(255, 200, 0))
            d.point((4, 4), fill=(255, 200, 0))
            
        elif name == 'arrow_down': # Seta Baixo
            d.polygon([(1, 2), (7, 2), (4, 6)], fill=(100, 149, 237))
            
        elif name == 'arrow_up': # Seta Cima
            d.polygon([(4, 2), (1, 6), (7, 6)], fill=(255, 69, 0))
            
        # Converte para RGB (fundo preto) para a matriz
        return img.convert('RGB')

    def _get_weather_desc(self, code):
        if code == 0: return "CEU LIMPO"
        if code == 1: return "ENSOLARADO"
        if code == 2: return "PARC. NUBLADO"
        if code == 3: return "NUBLADO"
        if code <= 48: return "NEBLINA"
        if code <= 57: return "CHUVISCO"
        if code <= 67: return "CHUVA"
        if code <= 77: return "NEVE"
        if code <= 82: return "PANCADAS"
        if code <= 86: return "NEVE"
        if code <= 99: return "TEMPESTADE"
        return ""

    def draw(self, canv):
        w = data.dados.get('weather', {})
        code = w.get('code', 0)
        
        hour = time.localtime().tm_hour
        
        # Usa is_day da API se disponivel (Mais preciso que horario fixo)
        if 'is_day' in w:
            is_night = w['is_day'] == 0
        else:
            is_night = hour >= 18 or hour < 6
        
        # --- 1. ZONA SUPERIOR (Y: 0 até 34) ---
        
        # Temperatura (X:2, Y:0) - Branco Quente
        # Usando font_xl (9x18B)
        temp_str = f"{w.get('temp', 0)}°"
        # Ajuste Y para baseline (aprox 14px para fonte 9x18)
        graphics.DrawText(canv, cfg.font_xl, 8, 18, self.C_WARM_WHITE, temp_str)
        
        # Cidade (X:4, Y:24) - Com recuo para hierarquia
        cidade = data.dados.get('cidade', 'SP').upper()
        if len(cidade) > 16: cidade = cidade[:16]
        graphics.DrawText(canv, cfg.font_s, 4, 28, self.C_LIGHT_GREY, cidade)
        
        # Descrição (X:4, Y:31) - Com recuo
        desc = self._get_weather_desc(code)
        graphics.DrawText(canv, cfg.font_t, 4, 35, cfg.C_DIM, desc)
        
        # Ícone do Clima (X:36, Y:2) - 24x24
        icon_name = 'cloud'
        if code == 0: icon_name = 'sun'
        elif code <= 3: icon_name = 'partly_cloudy'
        elif code >= 95: icon_name = 'storm'
        elif code >= 50: icon_name = 'rain'
        
        # Gera ícone animado (passando is_night)
        icon_weather = self._get_icon(icon_name, (24, 24), is_night, hour, w.get('wind', 0))
        
        # Animação de Flutuar (Posicionado em Y=0 para dar espaço embaixo)
        float_y = int(math.sin(time.time() * 1.5) * 1) 
        canv.SetImage(icon_weather, 38, 6 + float_y)
        
        # --- VARIAÇÃO TÉRMICA (Abaixo do ícone) ---
        min_val = f"{w.get('min', 0)}°"
        max_val = f"{w.get('max', 0)}°"
        
        x_pos = 4
        graphics.DrawText(canv, cfg.font_t, x_pos, 43, cfg.C_BLUE, min_val)
        x_pos += sum(cfg.font_t.CharacterWidth(ord(c)) for c in min_val)
        graphics.DrawText(canv, cfg.font_t, x_pos, 43, cfg.C_DIM, "/")
        x_pos += cfg.font_t.CharacterWidth(ord('/'))
        graphics.DrawText(canv, cfg.font_t, x_pos, 43, cfg.C_RED, max_val)
        x_pos += sum(cfg.font_t.CharacterWidth(ord(c)) for c in max_val)
        
        # Probabilidade de Chuva (Se houver)
        pop = w.get('pop', 0)
        if pop > 0:
            icon_pop = self._get_icon('pop', (8, 8))
            canv.SetImage(icon_pop, x_pos + 4, 37) # 4px de distancia
            graphics.DrawText(canv, cfg.font_t, x_pos + 13, 43, cfg.C_BLUE, f"{pop}%")
        
        # --- 2. LINHA DIVISÓRIA (Y: 44) ---
        graphics.DrawLine(canv, 2, 44, 61, 44, self.C_DARK_GREY)
        
        # --- 3. ZONA INFERIOR - GRID 2x2 (Fixa) ---
        
        # Quadrante 1 (Esq-Sup) - Umidade
        icon_hum = self._get_icon('humidity', (8, 8))
        canv.SetImage(icon_hum, 1, 45)
        graphics.DrawText(canv, cfg.font_s, 10, 52, cfg.C_BLUE, f"{w.get('humidity', 0)}%")
        
        # Quadrante 2 (Dir-Sup) - Vento
        icon_wind = self._get_icon('wind', (8, 8))
        canv.SetImage(icon_wind, 33, 45)
        wind_val = round(w.get('wind', 0))
        graphics.DrawText(canv, cfg.font_s, 42, 52, cfg.C_DIM, f"{wind_val}")
        
        # Quadrante 3 (Esq-Inf) - UV
        uv_val = round(w.get('uv', 0))
        graphics.DrawText(canv, cfg.font_t, 2, 61, cfg.C_ORANGE, "UV")
        
        # Barra UV (No lugar do valor)
        if uv_val < 3: uv_col = cfg.C_GREEN
        elif uv_val < 6: uv_col = cfg.C_YELLOW
        elif uv_val < 8: uv_col = cfg.C_ORANGE
        elif uv_val < 11: uv_col = cfg.C_RED
        else: uv_col = graphics.Color(153, 69, 255)
        
        # Barra UV Arredondada (Y=58, 59, 60 para centralizar com texto)
        # Fundo
        graphics.DrawLine(canv, 13, 58, 26, 58, cfg.C_GREY)
        graphics.DrawLine(canv, 12, 59, 27, 59, cfg.C_GREY)
        graphics.DrawLine(canv, 13, 60, 26, 60, cfg.C_GREY)
        # Barra UV Fixa (Escala Colorida)
        # Verde -> Amarelo -> Laranja -> Vermelho -> Violeta
        for i in range(16):
            x = 12 + i
            # Define cor baseada na posição da barra
            if i < 4: c = cfg.C_GREEN
            elif i < 8: c = cfg.C_YELLOW
            elif i < 11: c = cfg.C_ORANGE
            elif i < 14: c = cfg.C_RED
            else: c = graphics.Color(153, 69, 255)
            
            canv.SetPixel(x, 59, c.red, c.green, c.blue)
            if i > 0 and i < 15: # Arredonda cantos
                canv.SetPixel(x, 58, c.red, c.green, c.blue)
                canv.SetPixel(x, 60, c.red, c.green, c.blue)

        # Preenchimento
        bar_w = min(15, int(uv_val * 1.5))
        if bar_w > 0:
            graphics.DrawLine(canv, 12, 59, 12 + bar_w, 59, uv_col) # Meio
            if bar_w > 0: # Topo e Base (com recuo para arredondar)
                end_x = min(26, 12 + bar_w)
                if end_x >= 13:
                    graphics.DrawLine(canv, 13, 58, end_x, 58, uv_col)
                    graphics.DrawLine(canv, 13, 60, end_x, 60, uv_col)
        # Marcador de Valor (Branco)
        # Mapeia UV 0-11 para 0-15 pixels
        pos = int((min(uv_val, 11) / 11.0) * 15)
        mx = 12 + pos
        graphics.DrawLine(canv, mx, 58, mx, 60, cfg.C_WHITE)

        # Quadrante 4 (Dir-Inf) - Sensação Térmica
        st_val = w.get('feels_like', w.get('temp', 0))
        graphics.DrawText(canv, cfg.font_s, 33, 61, cfg.C_WHITE, f"ST {st_val}°")

# Instância única
weather_page = WeatherPage()

def draw(canv):
    weather_page.draw(canv)
