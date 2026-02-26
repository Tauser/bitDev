import time
import datetime
import os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from rgbmatrix import graphics
import config as cfg
import utils
import data

class ClockPage:
    def __init__(self):
        self.DEBUG = False # Mude para False para mostrar a hora real
        if self.DEBUG:
            self.debug_start_time = time.time()
            self.debug_epoch = datetime.datetime.now().replace(hour=12, minute=58, second=50)

        self.digits = [{'val': None, 'prev': None, 'start': 0} for _ in range(4)]
        
        # --- CONFIGURAÇÃO DA PLACA FLIP CLOCK ---
        self.card_w = 14  # OBRIGATÓRIO SER PAR (14) para não dar o Glitch de memória
        self.card_h = 28
        self.duration = 0.4 
        
        # --- CONFIGURAÇÃO DO CALENDÁRIO ---
        self.date_card_w = 7
        self.date_card_h = 14
        self.date_digits = [] # Lista dinâmica para os caracteres da data
        self.months = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
        self.cache_date = {}
        
        # --- CARREGAMENTO DA FONTE ---
        self.font = None
        
        # 1. Tenta carregar a fonte XL (10x20.bdf) para visual pixelado
        try:
            bdf_path = os.path.join(cfg.BASE_DIR, "fonts/10x20.bdf")
            if os.path.exists(bdf_path):
                self.font = ImageFont.truetype(bdf_path, 20)
        except: pass

        # 2. Fallback para TTF se não conseguir carregar a BDF
        if not self.font:
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
                "fonts/04B_03__.TTF"
            ]
            for p in font_paths:
                if os.path.exists(p):
                    try:
                        self.font = ImageFont.truetype(p, 45) # Tamanho da fonte base
                        break
                    except: pass
                
        if not self.font:
            try: self.font = ImageFont.load_default()
            except: pass

        # Pré-renderiza os números de 0 a 9 para não travar a matriz
        self.cache = {}
        self._prerender_assets()

    def _prerender_assets(self):
        """Gera as imagens estáticas das placas (Fundo 3D + Número Gigante)"""
        for i in range(10):
            s = str(i)
            # 1. Cria a Placa Cinza
            img = Image.new("RGB", (self.card_w, self.card_h), (20, 20, 20))
            d = ImageDraw.Draw(img)
            
            # Gloss superior
            d.rectangle((0, 0, self.card_w, self.card_h // 2 - 1), fill=(35, 35, 35))
            
            # Cantos pretos para arredondar a placa
            bg = (0, 0, 0)
            d.point([(0,0), (self.card_w-1, 0), (0, self.card_h-1), (self.card_w-1, self.card_h-1)], fill=bg)

            # 2. Desenha o número de forma segura e "gordinha"
            if self.font:
                try:
                    # Tela gigante transparente para renderizar o número puro
                    temp_size = 100
                    txt_img = Image.new("RGBA", (temp_size, temp_size), (0,0,0,0))
                    d_txt = ImageDraw.Draw(txt_img)
                    
                    # Desenha branco sólido
                    d_txt.text((20, 20), s, font=self.font, fill=(255,255,255,255))
                    
                    # A MÁGICA: Corta todo o espaço invisível em volta da letra
                    bbox = txt_img.getbbox() 
                    
                    if bbox:
                        txt_cropped = txt_img.crop(bbox)
                        
                        # Define o tamanho para ocupar toda a placa (deixando só 2px de borda)
                        target_w = self.card_w - 4
                        target_h = self.card_h - 6
                        
                        # Estica a imagem cortada
                        txt_resized = txt_cropped.resize((target_w, target_h), Image.NEAREST)
                        
                        # Cola no centro exato da placa
                        px = (self.card_w - target_w) // 2
                        py = (self.card_h - target_h) // 2
                        img.paste(txt_resized, (px, py), txt_resized)
                    else:
                        d.text((3, 10), s, fill=(255,255,255), font=self.font)
                except Exception as e:
                    print("Erro na fonte:", e)
                    d.text((3, 10), s, fill=(255,255,255))
            else:
                d.text((3, 10), s, fill=(255,255,255))

            # 3. Desenha o Corte Mecânico 3D por cima de tudo
            mid = self.card_h // 2
            d.line((0, mid, self.card_w, mid), fill=(0, 0, 0)) # Linha de corte preta sólida
            
            # Salva no cache convertido para RGB
            self.cache[s] = img.convert("RGB")

        # --- ASSETS DO CALENDÁRIO (Mini Placas) ---
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
        for c in chars:
            img = Image.new("RGB", (self.date_card_w, self.date_card_h), (20, 20, 20))
            d = ImageDraw.Draw(img)
            
            # Estilo Mini Placa (Gloss)
            d.rectangle((0, 0, self.date_card_w, self.date_card_h // 2 - 1), fill=(35, 35, 35))
            
            # Cantos arredondados (pixel art)
            bg = (0, 0, 0)
            d.point([(0,0), (self.date_card_w-1, 0), (0, self.date_card_h-1), (self.date_card_w-1, self.date_card_h-1)], fill=bg)

            if c != ' ':
                if self.font:
                    try:
                        # Renderiza grande e reduz para 3x5 (cabe no card 4x7)
                        temp_size = 40
                        txt_img = Image.new("RGBA", (temp_size, temp_size), (0,0,0,0))
                        d_txt = ImageDraw.Draw(txt_img)
                        d_txt.text((10, 10), c, font=self.font, fill=(200,200,200,255))
                        
                        bbox = txt_img.getbbox()
                        if bbox:
                            txt_cropped = txt_img.crop(bbox)
                            # Redimensiona para 5x10 pixels (Pixel Art Style) para caber no card de 7px
                            txt_resized = txt_cropped.resize((5, 10), Image.NEAREST)
                            # Centraliza no card 7x14
                            img.paste(txt_resized, (1, 2), txt_resized)
                        else:
                             d.text((0, 0), c, fill=(200,200,200))
                    except: pass
                else:
                    d.text((0, 0), c, fill=(200,200,200))
            
            # Linha de corte
            mid = self.date_card_h // 2
            d.line((0, mid, self.date_card_w, mid), fill=(0,0,0))
            self.cache_date[c] = img.convert("RGB")

    def draw(self, canv):
        now = datetime.datetime.now()
        
        if self.DEBUG:
            elapsed = time.time() - self.debug_start_time
            now = self.debug_epoch + datetime.timedelta(seconds=elapsed * 30)

        h, m = f"{now.hour:02d}", f"{now.minute:02d}"
        new_vals = [h[0], h[1], m[0], m[1]]
        
        for i, v in enumerate(new_vals):
            d = self.digits[i]
            if d['val'] != v:
                d['prev'], d['val'], d['start'] = d['val'], v, time.time()
                if d['prev'] is None: d['prev'] = v 

        canv.Fill(0, 0, 0) # Limpa a tela

        # --- LAYOUT DO RELÓGIO ---
        y_pos = 10 
        
        self._draw_digit(canv, 0, 0, y_pos)       # Hora 1 (x=0)
        self._draw_digit(canv, 1, 15, y_pos)      # Hora 2 (x=15)
        
        # Dois Pontos (Piscando suavemente no centro)
        if int(time.time() * 2) % 2 == 0:
            graphics.DrawLine(canv, 31, y_pos+9, 32, y_pos+9, cfg.C_WHITE)
            graphics.DrawLine(canv, 31, y_pos+10, 32, y_pos+10, cfg.C_WHITE)
            graphics.DrawLine(canv, 31, y_pos+18, 32, y_pos+18, cfg.C_WHITE)
            graphics.DrawLine(canv, 31, y_pos+19, 32, y_pos+19, cfg.C_WHITE)

        self._draw_digit(canv, 2, 35, y_pos)      # Minuto 1
        self._draw_digit(canv, 3, 50, y_pos)      # Minuto 2

        # --- CALENDÁRIO (Flip Style) ---
        # Formato: 25 FEV 26 (Sem cidade para caber maior)
        day = now.day
        mon = self.months[now.month - 1]
        yr = now.year % 100
        
        date_str = f"{day:02d} {mon} {yr:02d}"
        
        # Ajusta lista de estados se o tamanho da string mudar
        while len(self.date_digits) < len(date_str):
            self.date_digits.append({'val': None, 'prev': None, 'start': 0})
            
        # Renderiza a linha centralizada
        # Largura variável: Placas(7px) + Gaps(1px) + Espaços(3px)
        char_w = self.date_card_w
        gap = 1
        space_w = 3
        
        total_w = 0
        for c in date_str:
            if c == ' ': total_w += space_w
            else: total_w += char_w + gap
        total_w -= gap # Remove ultimo gap
        
        start_x = (64 - total_w) // 2
        y_date = 43
        
        current_x = start_x
        for i, char in enumerate(date_str):
            d = self.date_digits[i]
            if d['val'] != char:
                d['prev'] = d['val']
                d['val'] = char
                d['start'] = time.time()
                if d['prev'] is None: d['prev'] = char
            
            if char == ' ':
                current_x += space_w
            else:
                self._draw_date_card(canv, d, current_x, y_date)
                current_x += char_w + gap

    def _draw_digit(self, canv, idx, x, y):
        d = self.digits[idx]
        if d['val'] is None: return
        
        img_curr = self.cache.get(d['val'])
        img_prev = self.cache.get(d['prev'])
        if not img_curr: return
        
        p = (time.time() - d['start']) / self.duration
        if p >= 1.0 or d['prev'] is None:
            canv.SetImage(img_curr, x, y)
            return
            
        res = Image.new("RGB", (self.card_w, self.card_h))
        w, h = self.card_w, self.card_h
        h2 = h // 2
        
        res.paste(img_curr.crop((0, 0, w, h2)), (0, 0))
        res.paste(img_prev.crop((0, h2, w, h)), (0, h2))
        
        if p < 0.5:
            factor = 1.0 - (p * 2)
            fh = int(h2 * factor)
            if fh > 0:
                flap = img_prev.crop((0, 0, w, h2)).resize((w, fh), Image.NEAREST)
                flap = ImageEnhance.Brightness(flap).enhance(0.5 + 0.5*factor)
                res.paste(flap, (0, h2 - fh))
        else:
            factor = (p - 0.5) * 2
            fh = int(h2 * factor)
            if fh > 0:
                flap = img_curr.crop((0, h2, w, h)).resize((w, fh), Image.NEAREST)
                flap = ImageEnhance.Brightness(flap).enhance(0.5 + 0.5*factor)
                res.paste(flap, (0, h2))
        
        canv.SetImage(res.convert("RGB"), x, y)

    def _draw_date_card(self, canv, d, x, y):
        curr, prev = d['val'], d['prev']
        if curr is None or curr == ' ': return
        
        img_curr = self.cache_date.get(curr)
        img_prev = self.cache_date.get(prev)
        if not img_curr: return
        
        # Animação rápida para data (se mudar)
        p = (time.time() - d['start']) / 0.4
        if p >= 1.0 or prev is None:
            canv.SetImage(img_curr, x, y)
            return
            
        res = Image.new("RGB", (self.date_card_w, self.date_card_h))
        w, h = self.date_card_w, self.date_card_h
        h2 = h // 2
        
        res.paste(img_curr.crop((0, 0, w, h2)), (0, 0))
        res.paste(img_prev.crop((0, h2, w, h)), (0, h2))
        
        if p < 0.5:
            factor = 1.0 - (p * 2)
            fh = int(h2 * factor)
            if fh > 0:
                flap = img_prev.crop((0, 0, w, h2)).resize((w, fh), Image.NEAREST)
                res.paste(flap, (0, h2 - fh))
        else:
            factor = (p - 0.5) * 2
            fh = int(h2 * factor)
            if fh > 0:
                flap = img_curr.crop((0, h2, w, h)).resize((w, fh), Image.NEAREST)
                res.paste(flap, (0, h2))
        
        canv.SetImage(res.convert("RGB"), x, y)

# Inicialização Padrão
clock_page = ClockPage()

def draw(canv):
    clock_page.draw(canv)