from rgbmatrix import graphics
import config as cfg
import utils
import data
import time
import datetime

class AgendaPage:
    def __init__(self):
        self.scroll_states = {} # Guarda a posição X de cada título
        self.last_scroll_time = time.time()
        self.cycle_start = time.time()

    def draw(self, canv):
        events = data.dados.get('agenda', [])
        
        if not events:
            utils.draw_center(canv, cfg.font_s, 25, cfg.C_DIM, "NENHUM")
            utils.draw_center(canv, cfg.font_s, 35, cfg.C_DIM, "EVENTO")
            utils.draw_center(canv, cfg.font_t, 50, cfg.C_GREY, "Configure no Web")
            return

        now = datetime.datetime.now()
        
        # Layout: 6 Eventos (1 linha cada) - Ultra Compacto
        # Y start = 9 (Logo abaixo do header)
        # Altura por evento = 9px (8px badge + 1px linha)
        
        y_base = 9
        
        # Ciclo de Animação (10s total)
        # 0.0 - 6.0: Título (Mais tempo para leitura)
        # 6.0 - 6.5: Slide Cima
        # 6.5 - 9.5: Info (Hora/Tempo)
        # 9.5 - 10.0: Slide Cima
        
        t = (time.time() - self.cycle_start) % 10.0
        primary_type = 'TITLE'
        
        # Valor de "Esmagamento" para o efeito de persiana (0 = visível, 5 = fechado)
        squeeze_val = 0 
        
        if 0 <= t < 6.0:
            primary_type = 'TITLE'
            squeeze_val = 0
        elif 6.0 <= t < 6.25: # Fechando (Saída Título)
            primary_type = 'TITLE'
            squeeze_val = int((t - 6.0) / 0.25 * 5)
        elif 6.25 <= t < 6.5: # Abrindo (Entrada Info)
            primary_type = 'INFO'
            squeeze_val = int((6.5 - t) / 0.25 * 5)
        elif 6.5 <= t < 9.5:
            primary_type = 'INFO'
            squeeze_val = 0
        elif 9.5 <= t < 9.75: # Fechando (Saída Info)
            primary_type = 'INFO'
            squeeze_val = int((t - 9.5) / 0.25 * 5)
        else: # Abrindo (Entrada Título)
            primary_type = 'TITLE'
            squeeze_val = int((10.0 - t) / 0.25 * 5)

        # Atualiza scroll globalmente
        update_scroll = False
        if time.time() - self.last_scroll_time > 0.1: # Mais lento para leitura
            self.last_scroll_time = time.time()
            update_scroll = True

        # Desenha em ordem inversa (5 -> 0) para que a linha de cima cubra a de baixo (máscara)
        visible_events = events[:6]
        for i in range(len(visible_events) - 1, -1, -1):
            ev = visible_events[i]
            y = y_base + (i * 9)
            
            dt = ev['dt']
            if dt.tzinfo: dt = dt.astimezone().replace(tzinfo=None)
            
            # --- 1. PREPARAÇÃO DO BADGE (Dia ou Hora) ---
            # Calcula largura baseada no texto + 2px de cada lado
            is_today = dt.date() == now.date()
            dias_pt = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]
            badge_text = dias_pt[dt.weekday()]
            
            w_badge_txt = sum(cfg.font_t.CharacterWidth(ord(c)) for c in badge_text)
            badge_w = w_badge_txt + 2 # 2px esquerda + 2px direita
            
            if is_today:
                bg_col = cfg.C_ORANGE
                txt_col = graphics.Color(0,0,0) # Preto para contraste
            else:
                bg_col = cfg.C_MAT_TAIL
                txt_col = cfg.C_WHITE
            
            txt_area_x = badge_w + 2 # Margem de 1px após o badge
            
            # Prepara Textos
            title_text = ev['summary']
            
            delta = dt - now
            total_seconds = delta.total_seconds()
            if total_seconds < 0: info_text = "Agora"
            elif total_seconds < 3600: info_text = f"Em {int(total_seconds//60)}m"
            elif is_today: info_text = dt.strftime("%H:%M")
            else: info_text = dt.strftime("%d/%m %H:%M")

            # 1. Limpa área de texto
            for by in range(y, y+9):
                graphics.DrawLine(canv, txt_area_x, by, 63, by, graphics.Color(0,0,0))

            # 2. Desenha Texto(s)
            self._draw_text(canv, i, primary_type, title_text, info_text, txt_area_x, y + 7, update_scroll, txt_area_x)
            
            # 3. Aplica Efeito Persiana (Máscara Preta Topo/Base)
            if squeeze_val > 0:
                for k in range(squeeze_val):
                    graphics.DrawLine(canv, txt_area_x, y + k, 63, y + k, graphics.Color(0,0,0))     # Topo descendo
                    graphics.DrawLine(canv, txt_area_x, y + 8 - k, 63, y + 8 - k, graphics.Color(0,0,0)) # Base subindo

            # --- 3. DESENHA BADGE (Máscara por cima do texto) ---
            # Fundo do Badge (Altura 10px: 2px pad + 6px texto + 2px pad)
            for by in range(y, y+8): 
                graphics.DrawLine(canv, 0, by, badge_w, by, bg_col)
            
            # Texto do Badge Centralizado
            # x=2 (margem esquerda fixa de 2px)
            graphics.DrawText(canv, cfg.font_t, 2, y+7, txt_col, badge_text)
            
            # Linha separadora suave
            if i < 5:
                graphics.DrawLine(canv, 0, y+8, 63, y+8, cfg.C_GREY)

    def _draw_text(self, canv, idx, type, title, info, x, y, update_scroll, start_x):
        if type == 'TITLE':
            text = title
            text_width = sum(cfg.font_s.CharacterWidth(ord(c)) for c in text)
            if text_width <= (64 - x):
                graphics.DrawText(canv, cfg.font_s, x, y, cfg.C_WHITE, text)
                if idx in self.scroll_states: del self.scroll_states[idx]
            else:
                if idx not in self.scroll_states: self.scroll_states[idx] = x
                graphics.DrawText(canv, cfg.font_s, int(self.scroll_states[idx]), y, cfg.C_WHITE, text)
                if update_scroll:
                    self.scroll_states[idx] -= 1
                    # Reinicia no ponto 0 do texto (start_x) quando some totalmente
                    if self.scroll_states[idx] + text_width < x: self.scroll_states[idx] = start_x
        else:
            graphics.DrawText(canv, cfg.font_s, x, y, cfg.C_YELLOW, info)

agenda_page = AgendaPage()

def draw(canv):
    agenda_page.draw(canv)