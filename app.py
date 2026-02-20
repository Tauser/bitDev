from flask import Flask, render_template, request, redirect, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import json
import subprocess
import time
import os
import config as cfg
import requests
import shutil
import socket
import getpass

app = Flask(__name__)
app.secret_key = 'chave_secreta_crypto_monitor'
CONFIG_PATH = os.path.join(cfg.BASE_DIR, 'user_config.json')
PIXELART_FOLDER = os.path.join(cfg.BASE_DIR, 'images', 'pixelart')

# Garante que a pasta existe ao iniciar o sistema
if not os.path.exists(PIXELART_FOLDER):
    os.makedirs(PIXELART_FOLDER)

print(f">> [APP] Carregando rotas Web v2.1. Rodando como: {getpass.getuser()}")

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
            "cidade": "Sao_Paulo",
            "pages": [
                {"id": "DASHBOARD", "nome": "Dashboard Cripto", "enabled": True, "tempo": 30},
                {"id": "BOLSA",     "nome": "Bolsa & Mercado",  "enabled": True, "tempo": 15},
                {"id": "IMPRESSORA", "nome": "Impressora 3D",    "enabled": True, "tempo": 15},
                {"id": "CLIMA",     "nome": "Meteorologia",     "enabled": True, "tempo": 15},
                {"id": "GALERIA",   "nome": "Galeria PixelArt", "enabled": True, "tempo": 10}
            ]
        }

def salvar_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

def get_folder_size(folder):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def get_sys_metrics():
    m = {
        'cpu_temp': 0, 'ram_usage': 0, 
        'disk_usage': 0, 'disk_total': 0, 'disk_free': 0, 'disk_breakdown': [],
        'uptime': '--', 'cpu_load': 0, 'ip': '127.0.0.1', 'wifi_ssid': 'Desconectado'
    }
    
    # CPU Temp
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            m['cpu_temp'] = round(int(f.read()) / 1000, 1)
    except Exception as e: print(f"Erro CPU Temp: {e}")
    
    # Fallback CPU (vcgencmd)
    if m['cpu_temp'] == 0:
        try:
            out = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
            m['cpu_temp'] = float(out.replace("temp=", "").replace("'C", "").strip())
        except: pass

    # CPU Load (Média 1 min)
    try:
        with open("/proc/loadavg", "r") as f:
            m['cpu_load'] = f.read().split()[0]
    except Exception as e: print(f"Erro Load: {e}")

    # Uptime
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            days, rem = divmod(int(uptime_seconds), 86400)
            hours, rem = divmod(rem, 3600)
            minutes = rem // 60
            if days > 0: m['uptime'] = f"{days}d {hours}h {minutes}m"
            else: m['uptime'] = f"{hours}h {minutes}m"
    except Exception as e: print(f"Erro Uptime: {e}")
    
    try:
        mem = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(':')
                    mem[key] = int(parts[1])
        
        if 'MemTotal' in mem:
            total = mem['MemTotal']
            avail = mem.get('MemAvailable', mem.get('MemFree', 0))
            if total > 0:
                m['ram_usage'] = round(((total - avail) / total) * 100, 1)
    except Exception as e: print(f"Erro RAM: {e}")
    
    # Fallback RAM (free command)
    if m['ram_usage'] == 0:
        try:
            out = subprocess.check_output(['free', '-m']).decode().splitlines()[1].split()
            total = int(out[1])
            used = int(out[2])
            m['ram_usage'] = round((used / total) * 100, 1)
        except: pass
    
    try:
        # Usa o disco onde o projeto está rodando
        total, used, free = shutil.disk_usage(cfg.BASE_DIR)
        if total > 0:
            m['disk_usage'] = round((used / total) * 100, 1)
            m['disk_total'] = round(total / (1024**3), 1)
            m['disk_free'] = round(free / (1024**3), 1)
            
            # --- Análise Dinâmica de Pastas ---
            project_usage = 0
            folders = []
            
            # Escaneia pastas na raiz do projeto
            if os.path.exists(cfg.BASE_DIR):
                for entry in os.scandir(cfg.BASE_DIR):
                    if entry.is_dir() and not entry.name.startswith('.'): # Ignora ocultos
                        size = get_folder_size(entry.path)
                        if size > 1024*1024: # Mostra apenas pastas > 1MB
                            folders.append({'name': entry.name.capitalize(), 'size': size})
                            project_usage += size
            
            # Ordena por tamanho
            folders.sort(key=lambda x: x['size'], reverse=True)
            
            # Calcula o resto do sistema (Total Usado - Pastas do Projeto)
            system_usage = max(0, used - project_usage)
            
            # Monta a lista para o gráfico (Sistema + Top 4 pastas do projeto)
            # Cores para rotação
            colors = ['#a855f7', '#f59e0b', '#10b981', '#ec4899', '#6366f1']
            
            # 1. Sistema (Sempre primeiro)
            m['disk_breakdown'].append({
                'name': 'Sistema',
                'percent': (system_usage / total) * 100,
                'size_fmt': f"{system_usage / (1024**3):.1f}GB",
                'color': '#3b82f6' # Azul
            })
            
            # 2. Pastas do Projeto
            for i, f in enumerate(folders[:4]):
                m['disk_breakdown'].append({
                    'name': f['name'],
                    'percent': (f['size'] / total) * 100,
                    'size_fmt': f"{f['size'] / (1024**2):.0f}MB",
                    'color': colors[i % len(colors)]
                })
            
    except Exception as e: print(f"Erro Disk: {e}")

    # IP Local
    try:
        # Tenta via socket (precisa de rota para internet)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(('8.8.8.8', 1))
        m['ip'] = s.getsockname()[0]
        s.close()
    except:
        # Fallback: hostname -I (funciona localmente)
        try:
            cmd = ['hostname', '-I']
            if os.path.exists('/usr/bin/hostname'): cmd = ['/usr/bin/hostname', '-I']
            elif os.path.exists('/bin/hostname'): cmd = ['/bin/hostname', '-I']
            
            out = subprocess.check_output(cmd).decode().strip()
            if out: m['ip'] = out.split()[0]
        except:
            # Fallback IP (ip route)
            try:
                out = subprocess.check_output(['ip', 'route', 'get', '1.1.1.1']).decode()
                # "1.1.1.1 via ... src 192.168.X.X ..."
                m['ip'] = out.split('src')[1].split()[0]
            except Exception as e: print(f"Erro IP: {e}")

    # Wi-Fi SSID
    try:
        # Tenta caminhos comuns para iwgetid
        cmd = ['iwgetid', '-r']
        if os.path.exists('/sbin/iwgetid'): cmd = ['/sbin/iwgetid', '-r']
        elif os.path.exists('/usr/sbin/iwgetid'): cmd = ['/usr/sbin/iwgetid', '-r']
        
        ssid = subprocess.check_output(cmd).decode().strip()
        if ssid: m['wifi_ssid'] = ssid
    except:
        # Fallback final: Tenta ler do arquivo de config
        try:
            with open("/etc/wpa_supplicant/wpa_supplicant.conf", "r") as f:
                for line in f:
                    if "ssid=" in line:
                        m['wifi_ssid'] = line.split('=')[1].strip().strip('"')
                        break
        except Exception as e: print(f"Erro WiFi: {e}")

    return m

@app.route('/')
def index():
    config = ler_config()
    
    # Lista completa de páginas do sistema
    system_pages = [
        {"id": "DASHBOARD", "nome": "Dashboard Cripto", "enabled": True, "tempo": 30},
        {"id": "BOLSA",     "nome": "Bolsa & Mercado",  "enabled": True, "tempo": 15},
        {"id": "IMPRESSORA", "nome": "Impressora 3D",    "enabled": True, "tempo": 15},
        {"id": "CLIMA",     "nome": "Meteorologia",     "enabled": True, "tempo": 15},
        {"id": "GALERIA",   "nome": "Galeria PixelArt", "enabled": True, "tempo": 10}
    ]

    # Garante que a chave pages exista (para compatibilidade)
    if 'pages' not in config:
        config['pages'] = system_pages
        salvar_config(config)
    else:
        # Merge: Adiciona páginas novas que ainda não estão no config do usuário
        current_ids = [p['id'] for p in config['pages']]
        modified = False
        for page in system_pages:
            if page['id'] not in current_ids:
                config['pages'].append(page)
                modified = True
        
        if modified:
            salvar_config(config)
        
    # Listar GIFs locais para a galeria
    local_gifs = []
    if os.path.exists(PIXELART_FOLDER):
        local_gifs = [f for f in os.listdir(PIXELART_FOLDER) if f.lower().endswith('.gif')]
        
    sys_data = get_sys_metrics()

    return render_template('index.html', 
                           moedas=config['secundarias'], 
                           brilho=config.get('brilho', 50),
                           cidade=config.get('cidade', 'Sao_Paulo'),
                           lat=config.get('lat', ''),
                           lon=config.get('lon', ''),
                           noturno=config.get('modo_noturno', False),
                           pages=config['pages'],
                           printer_ip=config.get('printer_ip', ''),
                           printer_name=config.get('printer_name', 'VORON 2.4'),
                           gifs=local_gifs,
                           cpu_temp=sys_data['cpu_temp'],
                           ram_usage=sys_data['ram_usage'],
                           disk_usage=sys_data['disk_usage'],
                           disk_total=sys_data['disk_total'],
                           disk_free=sys_data['disk_free'],
                           disk_breakdown=sys_data['disk_breakdown'],
                           cpu_load=sys_data['cpu_load'],
                           uptime=sys_data['uptime'],
                           wifi_ssid=sys_data['wifi_ssid'],
                           ip=sys_data['ip'])

@app.route('/brilho', methods=['POST'])
def ajustar_brilho():
    nivel = request.form.get('nivel')
    config = ler_config()
    config['brilho'] = int(nivel)
    config['last_brilho_change'] = time.time()
    salvar_config(config)
    return jsonify({'message': f'Brilho ajustado para {nivel}%', 'status': 'success'})

@app.route('/salvar_clima', methods=['POST'])
def salvar_clima():
    cidade = request.form.get('cidade')
    lat = request.form.get('latitude')
    lon = request.form.get('longitude')
    
    config = ler_config()
    
    if cidade:
        config['cidade'] = cidade
        
    if lat and lon:
        try:
            config['lat'] = float(lat)
            config['lon'] = float(lon)
            config['manual_coords'] = True
        except ValueError:
            return jsonify({'message': 'Latitude/Longitude inválidas.', 'status': 'error'})
    else:
        config['manual_coords'] = False
        config.pop('lat', None)
        config.pop('lon', None)
        
    salvar_config(config)
    msg = f"Cidade definida para {cidade}!" + (" (Coords Manuais)" if config.get('manual_coords') else "")
    return jsonify({'message': msg, 'status': 'success'})

@app.route('/alternar_noturno')
def alternar_noturno():
    config = ler_config()
    config['modo_noturno'] = not config.get('modo_noturno', False)
    salvar_config(config)
    return redirect('/')

@app.route('/adicionar', methods=['POST'])
def adicionar():
    simbolo = request.form.get('simbolo').upper().strip()
    if simbolo and not simbolo.endswith('USDT'): simbolo += 'USDT'
    
    # --- VALIDAÇÃO: Verifica se a moeda existe na Binance ---
    try:
        test_url = f"https://api.binance.com/api/v3/ticker/price?symbol={simbolo}"
        r = requests.get(test_url, timeout=2)
        if r.status_code != 200:
            return jsonify({'message': f"Erro: A moeda '{simbolo}' não foi encontrada na Binance!", 'status': 'error'})
    except:
        return jsonify({'message': "Erro: Falha na conexão ao validar moeda.", 'status': 'error'})

    config = ler_config()
    if simbolo and simbolo not in config['secundarias']:
        config['secundarias'].append(simbolo)
        salvar_config(config)
    return jsonify({'message': f'{simbolo} adicionada com sucesso!', 'status': 'success'})

@app.route('/reordenar_moedas', methods=['POST'])
def reordenar_moedas():
    data = request.get_json()
    if not data or 'moedas' not in data: return jsonify({'error': 'Dados invalidos'}), 400
    
    config = ler_config()
    novas = data['moedas']
    
    # Garante integridade: mantem apenas moedas que ja existiam, na nova ordem
    atuais = set(config['secundarias'])
    final = [m for m in novas if m in atuais]
    
    # Se sobrou alguma (erro de sync), adiciona no final
    for m in config['secundarias']:
        if m not in final: final.append(m)
        
    config['secundarias'] = final
    salvar_config(config)
    return jsonify({'success': True})

@app.route('/remover/<simbolo>')
def remover(simbolo):
    config = ler_config()
    if simbolo in config['secundarias']:
        config['secundarias'].remove(simbolo)
        salvar_config(config)
    return jsonify({'message': f'{simbolo} removida.', 'status': 'success'})

@app.route('/salvar_playlist', methods=['POST'])
def salvar_playlist():
    data = request.get_json()
    if not data or 'pages' not in data:
        return jsonify({'message': 'Dados inválidos', 'status': 'error'})
        
    config = ler_config()
    current_pages_map = {p['id']: p for p in config.get('pages', [])}
    
    new_pages = []
    for p_in in data['pages']:
        pid = p_in.get('id')
        if pid in current_pages_map:
            page = current_pages_map[pid]
            page['enabled'] = bool(p_in.get('enabled'))
            page['tempo'] = int(p_in.get('tempo'))
            new_pages.append(page)
    
    # Adiciona páginas que possam ter faltado (segurança)
    for pid, page in current_pages_map.items():
        if pid not in [p['id'] for p in new_pages]:
            new_pages.append(page)
            
    config['pages'] = new_pages
    salvar_config(config)
    return jsonify({'message': 'Playlist salva e reordenada!', 'status': 'success'})

@app.route('/salvar_printer', methods=['POST'])
def salvar_printer():
    ip = request.form.get('printer_ip')
    name = request.form.get('printer_name')
    config = ler_config()
    config['printer_ip'] = ip
    config['printer_name'] = name
    salvar_config(config)
    return jsonify({'message': 'Configurações da impressora salvas!', 'status': 'success'})

@app.route('/reiniciar')
def reiniciar_painel():
    # Agenda o reinicio para daqui a 1 segundo em background
    # Isso permite retornar o redirect para o navegador antes do servidor morrer
    def restart_later():
        time.sleep(1)
        subprocess.run(['sudo', 'systemctl', 'restart', 'crypto.service'])
    
    import threading
    threading.Thread(target=restart_later).start()
    
    flash("Reiniciando painel... Aguarde 10s.", 'success')
    return redirect('/')

@app.route('/desligar')
def desligar_sistema():
    flash("Desligando sistema... Aguarde.", 'success')
    subprocess.run(['sudo', 'shutdown', 'now'])
    return redirect('/')

@app.route('/wifi_reset')
def wifi_reset():
    try:
        # Força o wpa_supplicant a reler a configuração e reconectar
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'])
        flash("Comando de reconexão Wi-Fi enviado.", 'success')
    except Exception as e:
        flash(f"Erro ao tentar reconectar: {e}", 'error')
    return redirect('/')

@app.route('/salvar_wifi', methods=['POST'])
def salvar_wifi():
    ssid = request.form.get('ssid')
    psk = request.form.get('psk')
    
    if not ssid or not psk:
        flash("Erro: SSID e Senha são obrigatórios.", 'error')
        return redirect('/')
        
    # Cria o conteúdo do arquivo wpa_supplicant
    config_content = f"""country=BR\nctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\n\nnetwork={{\n    ssid="{ssid}"\n    psk="{psk}"\n}}\n"""
    
    try:
        # Salva em um arquivo temporário e move com sudo (para garantir permissão)
        tmp_path = "/tmp/wpa_supplicant.conf"
        with open(tmp_path, "w") as f:
            f.write(config_content)
        subprocess.run(['sudo', 'mv', tmp_path, '/etc/wpa_supplicant/wpa_supplicant.conf'], check=True)
        subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], check=True)
        flash(f"Wi-Fi configurado para '{ssid}'. Tentando conectar...", 'success')
    except Exception as e:
        flash(f"Erro ao salvar Wi-Fi: {e}", 'error')
    return jsonify({'message': 'Configuração Wi-Fi enviada. O painel tentará reconectar.', 'status': 'info'})

# --- ROTAS DE API E SISTEMA ---

@app.route('/api/status')
def api_status():
    """Retorna status do hardware (CPU, RAM, Disco)"""
    return jsonify(get_sys_metrics())

@app.route('/upload_gif', methods=['POST'])
def upload_gif():
    if 'file' not in request.files: return jsonify({'message': 'Nenhum arquivo enviado.', 'status': 'error'})
    file = request.files['file']
    if file.filename == '': return jsonify({'message': 'Nome do arquivo vazio.', 'status': 'error'})
    
    if file and file.filename.lower().endswith('.gif'):
        if not os.path.exists(PIXELART_FOLDER): os.makedirs(PIXELART_FOLDER)
        
        # Renomeação sequencial (1.gif, 2.gif...)
        existing_files = [f for f in os.listdir(PIXELART_FOLDER) if f.lower().endswith('.gif')]
        max_num = 0
        for f in existing_files:
            try:
                num = int(os.path.splitext(f)[0])
                if num > max_num: max_num = num
            except ValueError: pass
            
        filename = f"{max_num + 1}.gif"
        save_path = os.path.join(PIXELART_FOLDER, filename)
        
        file.save(save_path)
        try: os.chmod(save_path, 0o666) # Permite editar via SFTP depois
        except: pass
        
        return jsonify({'message': f'GIF enviado como "{filename}"!', 'status': 'success'})
    else:
        return jsonify({'message': 'Apenas arquivos .gif são permitidos.', 'status': 'error'})

@app.route('/delete_gif/<filename>')
def delete_gif(filename):
    try:
        filename = secure_filename(filename)
        path = os.path.join(PIXELART_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)
            return jsonify({'message': 'GIF removido.', 'status': 'success'})
    except: pass
    return jsonify({'message': 'Erro ao remover GIF.', 'status': 'error'})

@app.route('/search_gif')
def search_gif():
    query = request.args.get('q', '')
    pos = request.args.get('pos', '')
    if not query: return jsonify({'results': [], 'next': ''})
    
    # Proxy para Tenor API
    try:
        url = f"https://g.tenor.com/v1/search?q={query}&key=LIVDSRZULELA&limit=8&media_filter=minimal"
        if pos: url += f"&pos={pos}"
        
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            results = []
            for item in data.get('results', []):
                media = item['media'][0]['tinygif']
                results.append({'name': item.get('content_description', 'gif'), 'url': media['url'], 'preview': media['preview']})
            return jsonify({'results': results, 'next': data.get('next', '')})
    except: pass
    return jsonify({'results': [], 'next': ''})

@app.route('/download_gif', methods=['POST'])
def download_gif():
    url = request.form.get('url')
    name = request.form.get('name', 'download')
    if not url: return redirect('/')
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            filename = secure_filename(f"{name}.gif")
            if not filename.lower().endswith('.gif'): filename += ".gif"
            if not os.path.exists(PIXELART_FOLDER): os.makedirs(PIXELART_FOLDER)
            
            save_path = os.path.join(PIXELART_FOLDER, filename)
            with open(save_path, 'wb') as f: f.write(r.content)
            try: os.chmod(save_path, 0o666)
            except: pass
            return jsonify({'message': 'GIF baixado com sucesso!', 'status': 'success'})
    except Exception as e:
        return jsonify({'message': f'Erro no download: {e}', 'status': 'error'})

@app.route('/pixelart/<path:filename>')
@app.route('/images/pixelart/<path:filename>')
def serve_pixelart(filename):
    return send_from_directory(PIXELART_FOLDER, filename)

@app.route('/measure_speed')
def measure_speed():
    ping = "Err"
    dl = "--"
    try:
        # Ping Google DNS (1 pacote, timeout 1s)
        out = subprocess.check_output(['ping', '-c', '1', '-W', '1', '8.8.8.8'], stderr=subprocess.STDOUT).decode()
        if 'time=' in out:
            t = out.split('time=')[1].split(' ')[0]
            ping = f"{int(float(t))}ms"
    except: pass
    
    try:
        # Download teste (500KB via Cloudflare)
        start = time.time()
        requests.get("https://speed.cloudflare.com/__down?bytes=500000", timeout=5)
        duration = time.time() - start
        if duration > 0.01:
            speed = 4.0 / duration # 4 Megabits / tempo
            dl = f"{speed:.1f} Mbps"
    except: pass
    
    return jsonify({'ping': ping, 'download': dl})

@app.route('/logs')
def get_logs():
    try:
        # Busca os ultimos 100 logs do servico
        out = subprocess.check_output(['journalctl', '-u', 'crypto.service', '-n', '100', '--no-pager']).decode()
        return out
    except Exception as e:
        return f"Erro ao buscar logs: {e}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
