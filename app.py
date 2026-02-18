from flask import Flask, render_template, request, redirect, flash, send_from_directory, jsonify
import json
from werkzeug.utils import secure_filename
import subprocess
import time
import os
import config as cfg
import requests
import shutil
from datetime import timedelta
import socket

app = Flask(__name__)
app.secret_key = 'chave_secreta_crypto_monitor'
CONFIG_PATH = os.path.join(cfg.BASE_DIR, 'moedas.json')
PIXELART_FOLDER = os.path.join(cfg.BASE_DIR, 'images/pixelart')

DEFAULT_LIBRARY = [
    {"name": "Nyan Cat", "url": "https://media.tenor.com/2roX3uxz_68AAAAM/cat-space.gif"},
    {"name": "Mario Run", "url": "https://media.tenor.com/N_8P2rX3yJAAAAAM/mario-running.gif"},
    {"name": "Pacman", "url": "https://media.tenor.com/images/01a50c3b5364413b46d24023e4458e6e/tenor.gif"},
    {"name": "Sonic", "url": "https://media.tenor.com/P_e9_3j3V5gAAAAM/sonic-run.gif"},
    {"name": "Pikachu", "url": "https://media.tenor.com/fSsxHn4tS4QAAAAM/pikachu-running.gif"},
    # Vibe / Ambiente
    {"name": "Cyber City", "url": "https://media.tenor.com/images/193959455743957281163e3f90815219/tenor.gif"},
    {"name": "Rain", "url": "https://media.tenor.com/bC57M4vTj6IAAAAM/rain-pixel-art.gif"},
    {"name": "Sunset", "url": "https://media.tenor.com/images/1c3d22588377c0589337533109282306/tenor.gif"},
    {"name": "Coffee", "url": "https://media.tenor.com/5a7USwwt_lQAAAAM/coffee-pixel-art.gif"},
    {"name": "Fire", "url": "https://media.tenor.com/G_0j2eH-f60AAAAM/pixel-fire.gif"},
    # Sci-Fi / Tech
    {"name": "Matrix", "url": "https://media.tenor.com/2_fC2s0t_iwAAAAM/matrix-code.gif"},
    {"name": "Glitch", "url": "https://media.tenor.com/BfR_W3D0i1wAAAAM/pixel-glitch.gif"},
    {"name": "Invaders", "url": "https://media.tenor.com/images/14a33df945daac773e12096c469c4039/tenor.gif"},
    {"name": "Loading", "url": "https://media.tenor.com/G7LfW0O5qF8AAAAM/loading-pixel.gif"}
]

def ler_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except:
        return {
            "secundarias": ["ETHUSDT"], 
            "brilho": 50, 
            "last_brilho_change": 0, 
            "modo_noturno": False,
            "msg_custom": "",
            "cidade": "Sao_Paulo",
            "pages": [
                {"id": "DASHBOARD", "nome": "Dashboard Cripto", "enabled": True, "tempo": 30},
                {"id": "BOLSA",     "nome": "Bolsa & Mercado",  "enabled": True, "tempo": 15},
                {"id": "IMPRESSORA", "nome": "Impressora 3D",    "enabled": True, "tempo": 15},
                {"id": "GALERIA",   "nome": "Galeria PixelArt", "enabled": True, "tempo": 10}
            ]
        }

def salvar_config(config):
    tmp_path = CONFIG_PATH + ".tmp"
    bak_path = CONFIG_PATH + ".bak"
    try:
        with open(tmp_path, 'w') as f:
            json.dump(config, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(CONFIG_PATH): shutil.copy2(CONFIG_PATH, bak_path)
        os.replace(tmp_path, CONFIG_PATH)
    except Exception as e:
        print(f"Erro crítico ao salvar config: {e}")

@app.route('/')
def index():
    config = ler_config()
    if 'pages' not in config:
        config['pages'] = [
            {"id": "DASHBOARD", "nome": "Dashboard Cripto", "enabled": True, "tempo": 30},
            {"id": "BOLSA",     "nome": "Bolsa & Mercado",  "enabled": True, "tempo": 15},
            {"id": "GALERIA",   "nome": "Galeria PixelArt", "enabled": True, "tempo": 10}
        ]
        salvar_config(config)
        
    lista_gifs = []
    if os.path.exists(PIXELART_FOLDER):
        lista_gifs = [f for f in os.listdir(PIXELART_FOLDER) if f.lower().endswith('.gif')]
        lista_gifs.sort()

    total, used, free = shutil.disk_usage("/")
    disk_free = round(free / (1024**3), 1)
    disk_total = round(total / (1024**3), 1)
    disk_percent = int((used / total) * 100)

    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            cpu_temp = round(int(f.read()) / 1000, 1)
    except:
        cpu_temp = 0

    uptime_str = "N/A"
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_str = str(timedelta(seconds=int(uptime_seconds)))
    except: pass

    ram_percent = 0
    ram_total_mb = 0
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = {line.split(':')[0]: int(line.split(':')[1].split()[0]) for line in f}
        
        ram_total_mb = round(meminfo['MemTotal'] / 1024)
        ram_available_mb = round(meminfo['MemAvailable'] / 1024)
        ram_used_mb = ram_total_mb - ram_available_mb
        ram_percent = int((ram_used_mb / ram_total_mb) * 100)
    except: pass

    load_1m = 0
    try:
        with open('/proc/loadavg', 'r') as f:
            load_1m = float(f.read().split()[0])
    except: pass

    wifi_percent = 0
    try:
        with open('/proc/net/wireless', 'r') as f:
            for line in f:
                if "wlan0" in line:
                    quality = float(line.split()[2].replace('.', ''))
                    wifi_percent = int((quality / 70) * 100)
                    if wifi_percent > 100: wifi_percent = 100
    except: pass

    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except: 
        pass
        
    library_gifs = DEFAULT_LIBRARY

    return render_template('index.html', 
                           moedas=config['secundarias'], 
                           brilho=config.get('brilho', 50),
                           noturno=config.get('modo_noturno', False),
                           msg_custom=config.get('msg_custom', ''),
                           pages=config['pages'],
                           printer_ip=config.get('printer_ip', ''),
                           printer_name=config.get('printer_name', 'VORON 2.4'),
                           gifs=lista_gifs,
                           disk_free=disk_free,
                           disk_total=disk_total,
                           disk_percent=disk_percent,
                           cpu_temp=cpu_temp,
                           uptime=uptime_str,
                           ram_percent=ram_percent,
                           ram_total=ram_total_mb,
                           load_1m=load_1m,
                           wifi_percent=wifi_percent,
                           local_ip=local_ip,
                           library=library_gifs)

@app.route('/brilho', methods=['POST'])
def ajustar_brilho():
    nivel = request.form.get('nivel')
    config = ler_config()
    config['brilho'] = int(nivel)
    config['last_brilho_change'] = time.time()
    salvar_config(config)
    return redirect('/')

@app.route('/alternar_noturno')
def alternar_noturno():
    config = ler_config()
    config['modo_noturno'] = not config.get('modo_noturno', False)
    salvar_config(config)
    status = "ATIVADO" if config['modo_noturno'] else "DESATIVADO"
    flash(f"Modo Noturno {status}", 'control_success')
    return redirect('/')

@app.route('/adicionar', methods=['POST'])
def adicionar():
    simbolo = request.form.get('simbolo').upper().strip()
    if simbolo and not simbolo.endswith('USDT'): simbolo += 'USDT'
    
    try:
        test_url = f"https://api.binance.com/api/v3/ticker/price?symbol={simbolo}"
        r = requests.get(test_url, timeout=2)
        if r.status_code != 200:
            flash(f"Erro: A moeda '{simbolo}' não foi encontrada na Binance!", 'coin_error')
            return redirect('/')
    except:
        flash("Erro: Falha na conexão ao validar moeda.", 'coin_error')
        return redirect('/')

    config = ler_config()
    if simbolo and simbolo not in config['secundarias']:
        config['secundarias'].append(simbolo)
        salvar_config(config)
    return redirect('/')

@app.route('/reordenar_moedas', methods=['POST'])
def reordenar_moedas():
    data = request.get_json()
    nova_ordem = data.get('moedas', [])
    if nova_ordem:
        config = ler_config()
        config['secundarias'] = nova_ordem
        salvar_config(config)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 400

@app.route('/remover/<simbolo>')
def remover(simbolo):
    config = ler_config()
    if simbolo in config['secundarias']:
        config['secundarias'].remove(simbolo)
        salvar_config(config)
        flash(f"Moeda {simbolo} removida.", 'coin_success')
    return redirect('/')

@app.route('/salvar_playlist', methods=['POST'])
def salvar_playlist():
    config = ler_config()
    novas_paginas = []
    
    for page in config.get('pages', []):
        pid = page['id']
        enabled = request.form.get(f"enable_{pid}") == "on"
        tempo = int(request.form.get(f"time_{pid}", 15))
        page['enabled'] = enabled
        page['tempo'] = tempo
    
    salvar_config(config)
    flash("Configurações de tela salvas.", 'playlist_success')
    return redirect('/')

@app.route('/salvar_printer', methods=['POST'])
def salvar_printer():
    ip = request.form.get('printer_ip')
    name = request.form.get('printer_name')
    config = ler_config()
    config['printer_ip'] = ip
    config['printer_name'] = name
    salvar_config(config)
    flash("Configuração da impressora salva.", 'printer_success')
    return redirect('/')

@app.route('/reiniciar')
def reiniciar_painel():
    subprocess.run(['sudo', 'systemctl', 'restart', 'crypto.service'])
    return redirect('/')

@app.route('/desligar')
def desligar_sistema():
    subprocess.run(['sudo', 'shutdown', 'now'])
    return "Sistema desligando... Pode remover da tomada em 30 segundos."

@app.route('/salvar_msg', methods=['POST'])
def salvar_msg():
    msg = request.form.get('msg', '')
    config = ler_config()
    config['msg_custom'] = msg
    salvar_config(config)
    flash("Mensagem do letreiro atualizada.", 'control_success')
    return redirect('/')

@app.route('/limpar_msg')
def limpar_msg():
    config = ler_config()
    config['msg_custom'] = ""
    salvar_config(config)
    flash("Mensagem do letreiro removida.", 'control_success')
    return redirect('/')

@app.route('/wifi_reset')
def wifi_reset():
    try:
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'])
        flash("Comando de reconexão Wi-Fi enviado.", 'wifi_success')
    except Exception as e:
        flash(f"Erro ao tentar reconectar: {e}", 'wifi_error')
    return redirect('/')

@app.route('/salvar_wifi', methods=['POST'])
def salvar_wifi():
    ssid = request.form.get('ssid')
    psk = request.form.get('psk')
    
    if not ssid or not psk:
        flash("Erro: SSID e Senha são obrigatórios.", 'wifi_error')
        return redirect('/')
        
    config_content = f"""country=BR\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\n\nnetwork={{\n    ssid="{ssid}"\n    psk="{psk}"\n}}\n"""
    
    try:
        tmp_path = "/tmp/wpa_supplicant.conf"
        with open(tmp_path, "w") as f:
            f.write(config_content)
        subprocess.run(['sudo', 'mv', tmp_path, '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], check=True)
        flash(f"Wi-Fi configurado para '{ssid}'. Tentando conectar...", 'wifi_success')
    except Exception as e:
        flash(f"Erro ao salvar Wi-Fi: {e}", 'wifi_error')
    return redirect('/')

@app.route('/pixelart/<filename>')
def serve_pixelart(filename):
    return send_from_directory(PIXELART_FOLDER, filename)

@app.route('/upload_gif', methods=['POST'])
def upload_gif():
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'gallery_error')
        return redirect('/')
    
    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'gallery_error')
        return redirect('/')
        
    if file and file.filename.lower().endswith('.gif'):
        filename = secure_filename(file.filename)
        if not os.path.exists(PIXELART_FOLDER):
            os.makedirs(PIXELART_FOLDER)
        file.save(os.path.join(PIXELART_FOLDER, filename))
        flash(f'GIF "{filename}" enviado com sucesso!', 'gallery_success')
    else:
        flash('Apenas arquivos .gif são permitidos.', 'gallery_error')
        
    return redirect('/')

@app.route('/delete_gif/<filename>')
def delete_gif(filename):
    try:
        os.remove(os.path.join(PIXELART_FOLDER, secure_filename(filename)))
        flash(f'GIF "{filename}" removido.', 'gallery_success')
    except Exception as e:
        flash(f'Erro ao remover: {e}', 'gallery_error')
    return redirect('/')

@app.route('/logs')
def ver_logs():
    """Lê os logs do sistema e exibe em uma página simples"""
    try:
        output = subprocess.check_output(['sudo', 'journalctl', '-u', 'crypto.service', '-n', '100', '--no-pager']).decode('utf-8')
    except Exception as e:
        output = f"Erro ao ler logs: {e}"
    
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/measure_speed')
def measure_speed():
    """Mede Ping e Download"""
    ping = "..."
    try:
        t0 = time.time()
        requests.get('http://1.1.1.1', timeout=2)
        ping = f"{int((time.time() - t0) * 1000)}ms"
    except: ping = "Err"
    
    dl = "..."
    try:
        t0 = time.time()
        r = requests.get('http://speedtest.tele2.net/1MB.zip', timeout=5)
        dt = time.time() - t0
        size_bits = len(r.content) * 8
        speed_mbps = (size_bits / dt) / 1_000_000
        dl = f"{speed_mbps:.1f} Mbps"
    except: dl = "Err"
    
    return jsonify({'ping': ping, 'download': dl})

@app.route('/download_gif', methods=['POST'])
def download_gif():
    url = request.form.get('url')
    name = request.form.get('name')
    
    if not url or not name:
        flash('Erro: URL ou nome inválido.', 'gallery_error')
        return redirect('/')
        
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            filename = secure_filename(f"{name}.gif")
            with open(os.path.join(PIXELART_FOLDER, filename), 'wb') as f:
                f.write(r.content)
            flash(f'GIF "{filename}" baixado com sucesso!', 'gallery_success')
        else:
            flash('Erro ao baixar imagem (Status code inválido).', 'gallery_error')
    except Exception as e:
        flash(f'Erro no download: {e}', 'gallery_error')
        
    return redirect('/')

@app.route('/api/search_tenor')
def search_tenor():
    query = request.args.get('q', 'pixel art')
    pos = request.args.get('pos', '') # Parâmetro de paginação
    apikey = "LIVDSRZULELA" 
    lmt = 12
    
    search_term = f"{query} pixel art"
    
    try:
        url = f"https://g.tenor.com/v1/search?q={search_term}&key={apikey}&limit={lmt}&contentfilter=medium&ar_range=standard"
        if pos:
            url += f"&pos={pos}"
            
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            results = json.loads(r.content)
            gifs = [{'name': item['content_description'], 'url': item['media'][0]['tinygif']['url']} for item in results['results']]
            return jsonify({'results': gifs, 'next': results.get('next', '')})
    except: pass
    return jsonify({'results': [], 'next': ''})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
