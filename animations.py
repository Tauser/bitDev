import time
import random
import os
from PIL import Image, ImageSequence
from rgbmatrix import graphics
import config as cfg
import utils
import data

def garantir_cor(cor):
    if isinstance(cor, tuple):
        return graphics.Color(*cor)
    return cor

def processar_frame_inteligente(frame, box_w, box_h):
    """Redimensiona mantendo proporção e centraliza com fundo preto."""
    img = frame.convert("RGBA")
    src_w, src_h = img.size
    
    if src_w == 0 or src_h == 0: return img.convert("RGB")

    ratio = min(box_w / src_w, box_h / src_h)
    new_w = int(src_w * ratio)
    new_h = int(src_h * ratio)
    
    if new_w <= 0: new_w = 1
    if new_h <= 0: new_h = 1
    
    img = img.resize((new_w, new_h), Image.NEAREST)
    bg = Image.new("RGB", (box_w, box_h), (0, 0, 0))
    pos_x = (box_w - new_w) // 2
    pos_y = (box_h - new_h) // 2
    
    bg.paste(img, (pos_x, pos_y), img)
    return bg

def carregar_gif(caminho, w, h):
    frames = []
    try:
        if os.path.exists(caminho):
            img = Image.open(caminho)
            for frame in ImageSequence.Iterator(img):
                f = processar_frame_inteligente(frame, w, h)
                frames.append(f)
            print(f"GIF Carregado: {len(frames)} frames.")
        else:
            print(f"AVISO: GIF não encontrado: {caminho}")
    except Exception as e:
        print(f"Erro no GIF {caminho}: {e}")
    return frames

def fade_transition(matrix, target_brightness, speed=4):
    current = matrix.brightness
    step = speed if current < target_brightness else -speed
    if current == target_brightness: return

    faixa = range(current, target_brightness + step, step)
    for b in faixa:
        val = max(0, min(100, b))
        matrix.brightness = val
        time.sleep(0.01)
    matrix.brightness = target_brightness

def executar_matrix_rain(canvas, matrix):
    """Animação de Boot que espera os dados carregarem."""
    print("Iniciando Matrix Boot e aguardando dados...")
    
    cor_head = garantir_cor(getattr(cfg, 'C_MAT_HEAD', (200, 255, 200)))
    cor_tail = garantir_cor(getattr(cfg, 'C_MAT_TAIL', (0, 100, 0)))
    cor_texto = garantir_cor(cfg.C_TEAL)
    cor_dots  = garantir_cor(cfg.C_ORANGE)

    width = 64
    height = 64
    columns = [0] * width
    
    start_time = time.time()
    min_run_time = 5
    timeout = 60
    
    bar_w = 40
    bar_h = 4
    bar_x = (64 - bar_w) // 2
    bar_y = 45
    
    msgs_loading = ["system...", "network...", "data..."]
    msg_idx = 0
    char_idx = 0
    last_type_time = time.time()
    is_waiting = False
    last_wait_time = 0
    
    cor_loading = graphics.Color(120, 120, 120)

    while True:
        canvas.Clear()
        for x in range(0, width, 2):
            if columns[x] == 0:
                if random.random() > 0.9: columns[x] = 1
            else:
                columns[x] += 1
                if columns[x] > height + 5: columns[x] = 0
            
            y = columns[x]
            if y > 0 and y < height:
                canvas.SetPixel(x, y, cor_head.red, cor_head.green, cor_head.blue)
                for tail in range(1, 5):
                    if y - tail > 0:
                        canvas.SetPixel(x, y - tail, cor_tail.red, cor_tail.green, cor_tail.blue)

        utils.draw_center(canvas, cfg.font_l, 25, cor_texto, "BITDEV")
        
        if (time.time() - start_time > 15) and not data.dados.get('conexao', True):
             utils.draw_center(canvas, cfg.font_t, 35, cfg.C_RED, "SEM INTERNET")

        dados_ok = data.dados['status'].get('btc', False)
        elapsed = time.time() - start_time
        
        if dados_ok:
            progress = min(1.0, elapsed / min_run_time)
        else:
            progress = min(0.9, elapsed / min_run_time)
        
        graphics.DrawLine(canvas, bar_x, bar_y, bar_x + bar_w, bar_y, cor_texto)
        graphics.DrawLine(canvas, bar_x, bar_y + bar_h, bar_x + bar_w, bar_y + bar_h, cor_texto)
        graphics.DrawLine(canvas, bar_x, bar_y, bar_x, bar_y + bar_h, cor_texto)
        graphics.DrawLine(canvas, bar_x + bar_w, bar_y, bar_x + bar_w, bar_y + bar_h, cor_texto)
        
        fill_w = int(progress * (bar_w - 2))
        if fill_w > 0:
            for i in range(bar_h - 1):
                graphics.DrawLine(canvas, bar_x + 1, bar_y + 1 + i, bar_x + 1 + fill_w, bar_y + 1 + i, cor_dots)

        current_text = msgs_loading[msg_idx]
        
        if not is_waiting:
            if time.time() - last_type_time > 0.05:
                char_idx += 1
                last_type_time = time.time()
                if char_idx > len(current_text):
                    is_waiting = True
                    last_wait_time = time.time()
        else:
            if time.time() - last_wait_time > 1.5:
                is_waiting = False
                char_idx = 0
                msg_idx = (msg_idx + 1) % len(msgs_loading)

        full_w = sum(cfg.font_t.CharacterWidth(ord(c)) for c in current_text)
        start_x = (64 - full_w) // 2
        
        txt_display = current_text[:char_idx]
        
        if not is_waiting and char_idx < len(current_text):
            txt_display += chr(random.randint(33, 122))
            
        graphics.DrawText(canvas, cfg.font_t, start_x, 58, cor_loading, txt_display)
        
        canvas = matrix.SwapOnVSync(canvas)
        time.sleep(0.05)

        if elapsed > min_run_time:
            if dados_ok:
                print(">> Dados carregados! Iniciando Dashboard.")
                break
            
            if elapsed > timeout:
                print(">> Tempo limite excedido. Iniciando mesmo sem dados.")
                break