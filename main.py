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

# --- IMPORTAÇÃO DAS PÁGINAS ---
from pages import dashboard, bolsa, galeria, impressora

# --- FUNÇÃO WATCHDOG (SYSTEMD) ---
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

# --- 1. CONFIGURAÇÃO DO SERVIDOR WEB ---
def iniciar_web():
    try:
        web_app.app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Erro no servidor web: {e}")

print(">> Lançando Painel Web...")
threading.Thread(target=iniciar_web, daemon=True).start()

# --- 2. INICIALIZAÇÃO DO HARDWARE ---
print(">> Inicializando Hardware...")
matrix = RGBMatrix(options=cfg.options)
canvas = matrix.CreateFrameCanvas()

# Inicia thread de dados
data.iniciar_thread(matrix)

# --- 3. VARIÁVEIS GLOBAIS ---
indice_playlist = 0
ultimo_checkpoint = time.time()

# --- FUNÇÃO PARA LER PLAYLIST DINÂMICA ---
def obter_playlist_ativa():
    """Lê o JSON e retorna apenas as páginas ativadas"""
    try:
        path = os.path.join(cfg.BASE_DIR, 'moedas.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                d = json.load(f)
                # Filtra apenas as habilitadas
                paginas = [p for p in d.get('pages', []) if p.get('enabled', True)]
                
                # Se o usuário desativar tudo, força o Dashboard
                if not paginas:
                    return [{"id": "DASHBOARD", "tempo": 10}]
                return paginas
    except:
        pass
    
    # Fallback se der erro no arquivo
    return cfg.PLAYLIST

# Carrega a playlist inicial
playlist_atual = obter_playlist_ativa()

def realizar_transicao_fade():
    global indice_playlist, ultimo_checkpoint, playlist_atual
    
    animations.fade_transition(matrix, 0, cfg.FADE_SPEED)
    
    # Atualiza a lista (caso o usuário tenha mudado no site)
    playlist_atual = obter_playlist_ativa()
    
    # --- LÓGICA DE SKIP (Pular telas indisponíveis) ---
    # Tenta encontrar a próxima tela válida
    for _ in range(len(playlist_atual)):
        indice_playlist = (indice_playlist + 1) % len(playlist_atual)
        nova_tela = playlist_atual[indice_playlist]
        pid = nova_tela["id"]
        
        # --- LÓGICA INTELIGENTE: SÓ MOSTRA SE TIVER DADOS ---
        
        # 1. Impressora: Pula se estiver OFFLINE
        if pid == "IMPRESSORA" and not data.dados['status'].get('printer', False):
            continue
            
        # 2. Bolsa: Pula se não conseguiu buscar dados do Yahoo Finance
        if pid == "BOLSA" and not data.dados['status'].get('stocks', False):
            continue
            
        # 3. Dashboard: Se não tem BTC (sem internet), mas tem Galeria, pode pular o Dashboard
        # (Opcional: Se quiser ver o erro "Sem Rede", remova este if)
        # if pid == "DASHBOARD" and not data.dados['status'].get('btc', False):
        #    continue
        
        break # Tela válida encontrada (ou voltou para a mesma se for a única)
    
    if nova_tela["id"] == "GALERIA":
        galeria.sortear_novo()
    elif nova_tela["id"] == "DASHBOARD":
        dashboard.init()
    
    canvas.Clear()
    ultimo_checkpoint = time.time()
    
    brilho_alvo = data.dados.get('brilho', 70)
    animations.fade_transition(matrix, brilho_alvo, cfg.FADE_SPEED)

# --- 6. LOOP ---
print(">> Sistema Iniciado. Entrando no Loop...")
animations.executar_matrix_rain(canvas, matrix)

# Garante que o Dashboard comece do zero (sem pular slides) após o boot
if playlist_atual[indice_playlist]["id"] == "DASHBOARD":
    dashboard.init()

# --- CORREÇÃO: Reseta o timer para não pular a primeira página ---
# Isso garante que o sistema inicie no Dashboard e fique lá pelo tempo configurado
ultimo_checkpoint = time.time()

try:
    while True:
        sd_notify("WATCHDOG=1") # Ping: "Estou vivo!"
        try:
            agora = time.time()
            tela_config = playlist_atual[indice_playlist]
            
            if agora - ultimo_checkpoint > tela_config["tempo"]:
                realizar_transicao_fade()
                agora = time.time() 
                tela_config = playlist_atual[indice_playlist]

            canvas.Clear()

            # --- CORREÇÃO: Atualiza brilho em tempo real ---
            brilho_atual = data.dados.get('brilho', 70)
            if matrix.brightness != brilho_atual:
                matrix.brightness = brilho_atual

            # --- VERIFICAÇÃO DE CONEXÃO ---
            # Só bloqueia se a tela atual precisar de internet (Dashboard ou Bolsa)
            if not data.dados.get('conexao', True) and tela_config["id"] in ["DASHBOARD", "BOLSA"]:
                 canvas.Clear()
                 utils.draw_center(canvas, cfg.font_l, 22, cfg.C_RED, "SEM REDE")
                 
                 # Mostra IP para diagnóstico
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

            # --- LÓGICA DE LAYOUT ---
            if tela_config["id"] == "GALERIA":
                # Galeria ocupa a tela toda, sem header/footer
                galeria.draw(canvas)
                time.sleep(0.1)
            else:
                # 1. Desenha Header
                titulo = None
                if tela_config["id"] == "BOLSA": titulo = "MERCADO"
                if tela_config["id"] != "IMPRESSORA":
                    layout.draw_header(canvas, titulo)

                # 2. Desenha o Corpo da Página
                if tela_config["id"] == "DASHBOARD": dashboard.draw(canvas)
                elif tela_config["id"] == "BOLSA": bolsa.draw(canvas)
                elif tela_config["id"] == "IMPRESSORA": impressora.draw(canvas)

                # 3. Desenha Footer
                if tela_config["id"] != "IMPRESSORA":
                    layout.draw_footer(canvas)
                time.sleep(0.05)

            canvas = matrix.SwapOnVSync(canvas)
            
        except Exception as e:
            print(f"ERRO RECUPERÁVEL (Main Loop): {e}")
            time.sleep(1) # Espera um pouco para não sobrecarregar o log
            continue # Tenta o próximo frame sem fechar o programa

except KeyboardInterrupt:
    sys.exit(0)