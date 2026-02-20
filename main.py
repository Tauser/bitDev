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

from pages import dashboard, bolsa, galeria, impressora, clima
import utils

def sd_notify(msg):
    """Envia notificação para o systemd (Watchdog)"""
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
    """Lê o JSON e retorna apenas as páginas ativadas"""
    try:
        path = os.path.join(cfg.BASE_DIR, 'user_config.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                d = json.load(f)
                paginas = [p for p in d.get('pages', []) if p.get('enabled', True)]
                
                if not paginas:
                    return [{"id": "DASHBOARD", "tempo": 10}]
                return paginas
    except:
        pass
    
    return cfg.PLAYLIST

playlist_atual = obter_playlist_ativa()

def realizar_transicao_fade():
    global indice_playlist, ultimo_checkpoint, playlist_atual
    
    # 1. Carrega nova playlist para verificar mudanças
    nova_playlist = obter_playlist_ativa()
    if not nova_playlist: nova_playlist = [{"id": "DASHBOARD", "tempo": 10}]
    
    # Identifica ID da tela atual com segurança
    id_atual = ""
    if indice_playlist < len(playlist_atual):
        id_atual = playlist_atual[indice_playlist]["id"]
    
    # 2. Inicia Fade Out
    animations.fade_transition(matrix, 0, cfg.FADE_SPEED)
    
    # 3. CRÍTICO: Limpa a tela e atualiza o hardware PARA O PRETO antes de processar a próxima
    # Isso evita que a tela antiga fique "travada" ou "tremendo" enquanto a próxima carrega
    canvas.Clear()
    canvas = matrix.SwapOnVSync(canvas)
    
    # Atualiza playlist oficial
    playlist_atual = nova_playlist
    
    # Garante índice válido antes de procurar a próxima
    if indice_playlist >= len(playlist_atual): 
        indice_playlist = 0
    
    # 4. Encontra a próxima tela válida
    proximo_idx = indice_playlist
    proxima_tela = None
    
    # Tenta encontrar a próxima tela válida na sequência
    for i in range(1, len(playlist_atual) + 1):
        idx = (indice_playlist + i) % len(playlist_atual)
        cand = playlist_atual[idx]
        pid = cand["id"]
        
        # Filtros de Hardware
        if pid == "IMPRESSORA" and not data.dados['status'].get('printer', False): continue
        if pid == "BOLSA" and not data.dados['status'].get('stocks', False): continue
        
        proximo_idx = idx
        proxima_tela = cand
        break
    
    if proxima_tela is None:
        proximo_idx = 0
        proxima_tela = playlist_atual[0]
    
    indice_playlist = proximo_idx
    
    # 5. Inicializa a nova tela (Agora seguro, pois a tela já está preta)
    if proxima_tela["id"] == "GALERIA":
        galeria.sortear_novo()
    elif proxima_tela["id"] == "DASHBOARD":
        dashboard.init()
    
    ultimo_checkpoint = time.time()
    
    # 6. Fade In
    brilho_alvo = data.dados.get('brilho', 70)
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

            if tela_config["id"] == "GALERIA":
                galeria.draw(canvas)
                time.sleep(0.1)
            else:
                titulo = None
                if tela_config["id"] == "BOLSA": titulo = "MERCADO"
                
                header_col = cfg.C_TEAL
                if tela_config["id"] == "DASHBOARD": header_col = cfg.C_ORANGE
                elif tela_config["id"] == "BOLSA": header_col = cfg.C_BLUE
                
                if tela_config["id"] not in ["IMPRESSORA", "CLIMA"]:
                    layout.draw_header(canvas, titulo, header_col)

                if tela_config["id"] == "DASHBOARD": dashboard.draw(canvas)
                elif tela_config["id"] == "BOLSA": bolsa.draw(canvas)
                elif tela_config["id"] == "IMPRESSORA": impressora.draw(canvas)
                elif tela_config["id"] == "CLIMA": clima.draw(canvas)

                if tela_config["id"] not in ["IMPRESSORA", "CLIMA"]:
                    layout.draw_footer(canvas)
                time.sleep(0.05)

            canvas = matrix.SwapOnVSync(canvas)
            
        except Exception as e:
            print(f"ERRO RECUPERÁVEL (Main Loop): {e}")
            time.sleep(1)
            continue

except KeyboardInterrupt:
    sys.exit(0)