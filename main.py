import sys
import time
import threading
import json
import os
import socket
from rgbmatrix import RGBMatrix
import config as cfg
import data
import animations
import app as web_app
import layout

from pages import dashboard, bolsa, galeria, impressora, clima, relogio, agenda
import utils

def sd_notify(msg):
    sock = os.environ.get("NOTIFY_SOCKET")
    if not sock: return
    try:
        if sock.startswith("@"): sock = "\0" + sock[1:]
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.connect(sock)
            s.sendall(msg.encode())
    except: pass

def iniciar_web():
    try:
        web_app.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"CRITICO: Erro ao iniciar servidor web (Porta 5000 ocupada?): {e}")

print(">> Lançando Painel Web...")
threading.Thread(target=iniciar_web, daemon=True).start()

print(">> Inicializando Hardware...")
matrix = RGBMatrix(options=cfg.options)
canvas = matrix.CreateFrameCanvas()

data.iniciar_thread(matrix)

indice_playlist = 0
ultimo_checkpoint = time.time()

def obter_playlist_ativa():
    try:
        path = os.path.join(cfg.BASE_DIR, 'user_config.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                d = json.load(f)
                
                paginas = []
                now = time.localtime()
                curr_min = now.tm_hour * 60 + now.tm_min
                
                for p in d.get('pages', []):
                    if not p.get('enabled', True): continue
                    
                    # Verificação de Horário
                    inicio = p.get('inicio', '00:00')
                    fim = p.get('fim', '23:59')
                    
                    try:
                        ih, im = map(int, inicio.split(':'))
                        fh, fm = map(int, fim.split(':'))
                        start = ih * 60 + im
                        end = fh * 60 + fm
                        
                        if start <= end: # Horário normal (ex: 08:00 as 20:00)
                            if not (start <= curr_min <= end): continue
                        else: # Passa da meia-noite (ex: 22:00 as 06:00)
                            if not (curr_min >= start or curr_min <= end): continue
                    except: pass
                    
                    paginas.append(p)
                
                if not paginas:
                    return [{"id": "DASHBOARD", "tempo": 10}]
                return paginas
    except:
        pass
    
    return cfg.PLAYLIST

# Função auxiliar para desenhar qualquer tela (usada na transição)
def desenhar_tela_generica(canv, tela_conf):
    if tela_conf["id"] == "GALERIA":
        galeria.draw(canv)
    else:
        titulo = None
        if tela_conf["id"] == "BOLSA": titulo = "MERCADO"
        elif tela_conf["id"] == "AGENDA": titulo = "AGENDA"
        
        header_col = cfg.C_TEAL
        if tela_conf["id"] == "DASHBOARD": header_col = cfg.C_ORANGE
        elif tela_conf["id"] == "BOLSA": header_col = cfg.C_BLUE
        elif tela_conf["id"] == "AGENDA": header_col = cfg.C_GOLD
        
        if tela_conf["id"] not in ["IMPRESSORA", "CLIMA", "RELOGIO"]:
            layout.draw_header(canv, titulo, header_col)

        if tela_conf["id"] == "DASHBOARD": dashboard.draw(canv)
        elif tela_conf["id"] == "BOLSA": bolsa.draw(canv)
        elif tela_conf["id"] == "IMPRESSORA": impressora.draw(canv)
        elif tela_conf["id"] == "CLIMA": clima.draw(canv)
        elif tela_conf["id"] == "RELOGIO": relogio.draw(canv)
        elif tela_conf["id"] == "AGENDA": agenda.draw(canv)

        if tela_conf["id"] not in ["IMPRESSORA", "CLIMA", "RELOGIO", "AGENDA"]:
            layout.draw_footer(canv)

playlist_atual = obter_playlist_ativa()

def realizar_transicao_fade():
    global indice_playlist, ultimo_checkpoint, playlist_atual, canvas
    
    nova_playlist = obter_playlist_ativa()
    if not nova_playlist: nova_playlist = [{"id": "DASHBOARD", "tempo": 10}]
    
    id_atual = ""
    if indice_playlist < len(playlist_atual):
        id_atual = playlist_atual[indice_playlist]["id"]
    
    # 1. Efeito de Saída (Fade Out)
    animations.fade_transition(matrix, 0, cfg.FADE_SPEED)
    
    # Limpa a tela visualmente para garantir que não haja "rastro" durante o carregamento
    canvas.Clear()
    canvas = matrix.SwapOnVSync(canvas)
    
    playlist_atual = nova_playlist
    
    if indice_playlist >= len(playlist_atual): 
        indice_playlist = 0
    
    proximo_idx = indice_playlist
    proxima_tela = None
    
    for i in range(1, len(playlist_atual) + 1):
        idx = (indice_playlist + i) % len(playlist_atual)
        cand = playlist_atual[idx]
        pid = cand["id"]
        
        if pid == "IMPRESSORA" and not data.dados['status'].get('printer', False): continue
        if pid == "BOLSA" and not data.dados['status'].get('stocks', False): continue
        if pid == "GALERIA" and not galeria.tem_imagens(): continue
        
        proximo_idx = idx
        proxima_tela = cand
        break
    
    if proxima_tela is None:
        proximo_idx = 0
        proxima_tela = playlist_atual[0]
    
    indice_playlist = proximo_idx
    
    if proxima_tela["id"] == "GALERIA":
        galeria.sortear_novo()
    elif proxima_tela["id"] == "DASHBOARD":
        dashboard.init()
    
    canvas.Clear()
    desenhar_tela_generica(canvas, proxima_tela)
    canvas = matrix.SwapOnVSync(canvas)
    ultimo_checkpoint = time.time()
    
    # 3. Efeito de Entrada (Fade In)
    brilho_alvo = data.dados.get('brilho', 70)
    
    # Ajuste Noturno na Transição
    if data.dados.get('modo_noturno', False):
        h = time.localtime().tm_hour
        if h >= 22 or h < 6: brilho_alvo = min(brilho_alvo, 30)
        
    animations.fade_transition(matrix, brilho_alvo, cfg.FADE_SPEED)

print(">> Sistema Iniciado. Entrando no Loop...")
animations.executar_matrix_rain(canvas, matrix)

if playlist_atual[indice_playlist]["id"] == "DASHBOARD":
    dashboard.init()

ultimo_checkpoint = time.time()

try:
    while True:
        sd_notify("WATCHDOG=1")
        try:
            agora = time.time()
            tela_config = playlist_atual[indice_playlist]
            
            if agora - ultimo_checkpoint > tela_config["tempo"]:
                realizar_transicao_fade()
                agora = time.time() 
                tela_config = playlist_atual[indice_playlist]

            canvas.Clear()

            brilho_atual = data.dados.get('brilho', 70)
            
            # Auto Brilho Noturno (22h - 06h)
            if data.dados.get('modo_noturno', False):
                h = time.localtime().tm_hour
                if h >= 22 or h < 6: brilho_atual = min(brilho_atual, 30)

            if matrix.brightness != brilho_atual:
                matrix.brightness = brilho_atual

            if not data.dados.get('conexao', True) and tela_config["id"] in ["DASHBOARD", "BOLSA"]:
                 canvas.Clear()
                 utils.draw_center(canvas, cfg.font_l, 22, cfg.C_RED, "SEM REDE")
                 
                 ip = data.get_local_ip()
                 if ip != "127.0.0.1":
                     utils.draw_center(canvas, cfg.font_s, 38, cfg.C_TEAL, ip)
                     utils.draw_center(canvas, cfg.font_s, 48, cfg.C_YELLOW, "Sem Internet")
                 else:
                     utils.draw_center(canvas, cfg.font_s, 38, cfg.C_YELLOW, "Tentando")
                     utils.draw_center(canvas, cfg.font_s, 48, cfg.C_YELLOW, "Reconectar")
                     
                 canvas = matrix.SwapOnVSync(canvas)
                 time.sleep(0.5)
                 continue

            # Usa a nova função genérica também no loop principal
            desenhar_tela_generica(canvas, tela_config)
            time.sleep(0.05)

            canvas = matrix.SwapOnVSync(canvas)
            
        except Exception as e:
            print(f"ERRO RECUPERÁVEL (Main Loop): {e}")
            time.sleep(1)
            continue

except KeyboardInterrupt:
    sys.exit(0)