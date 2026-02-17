from flask import Flask, render_template, request, redirect, flash
import json
import subprocess
import time
import os
import config as cfg
import requests
import shutil

app = Flask(__name__)
app.secret_key = 'chave_secreta_crypto_monitor'
CONFIG_PATH = os.path.join(cfg.BASE_DIR, 'moedas.json')

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
        # 1. Salva em arquivo temporário primeiro (Segurança contra falha de energia)
        with open(tmp_path, 'w') as f:
            json.dump(config, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        # 2. Cria backup do atual e substitui o oficial (Operação atômica)
        if os.path.exists(CONFIG_PATH): shutil.copy2(CONFIG_PATH, bak_path)
        os.replace(tmp_path, CONFIG_PATH)
    except Exception as e:
        print(f"Erro crítico ao salvar config: {e}")

@app.route('/')
def index():
    config = ler_config()
    # Garante que a chave pages exista (para compatibilidade)
    if 'pages' not in config:
        config['pages'] = [
            {"id": "DASHBOARD", "nome": "Dashboard Cripto", "enabled": True, "tempo": 30},
            {"id": "BOLSA",     "nome": "Bolsa & Mercado",  "enabled": True, "tempo": 15},
            {"id": "GALERIA",   "nome": "Galeria PixelArt", "enabled": True, "tempo": 10}
        ]
        salvar_config(config)
        
    return render_template('index.html', 
                           moedas=config['secundarias'], 
                           brilho=config.get('brilho', 50),
                           noturno=config.get('modo_noturno', False),
                           pages=config['pages'],
                           printer_ip=config.get('printer_ip', ''),
                           printer_name=config.get('printer_name', 'VORON 2.4'))

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
            flash(f"Erro: A moeda '{simbolo}' não foi encontrada na Binance!", 'error')
            return redirect('/')
    except:
        flash("Erro: Falha na conexão ao validar moeda.", 'error')
        return redirect('/')

    config = ler_config()
    if simbolo and simbolo not in config['secundarias']:
        config['secundarias'].append(simbolo)
        salvar_config(config)
    return redirect('/')

@app.route('/remover/<simbolo>')
def remover(simbolo):
    config = ler_config()
    if simbolo in config['secundarias']:
        config['secundarias'].remove(simbolo)
        salvar_config(config)
    return redirect('/')

@app.route('/salvar_playlist', methods=['POST'])
def salvar_playlist():
    config = ler_config()
    novas_paginas = []
    
    # Reconstrói a lista baseada no form
    for page in config.get('pages', []):
        pid = page['id']
        # Checkbox: se não vier no form, é False
        enabled = request.form.get(f"enable_{pid}") == "on"
        tempo = int(request.form.get(f"time_{pid}", 15))
        page['enabled'] = enabled
        page['tempo'] = tempo
    
    salvar_config(config)
    return redirect('/')

@app.route('/salvar_printer', methods=['POST'])
def salvar_printer():
    ip = request.form.get('printer_ip')
    name = request.form.get('printer_name')
    config = ler_config()
    config['printer_ip'] = ip
    config['printer_name'] = name
    salvar_config(config)
    return redirect('/')

@app.route('/reiniciar')
def reiniciar_painel():
    subprocess.run(['sudo', 'systemctl', 'restart', 'crypto.service'])
    return redirect('/')

@app.route('/desligar')
def desligar_sistema():
    # Desligamento seguro para proteger o cartão SD
    subprocess.run(['sudo', 'shutdown', 'now'])
    return "Sistema desligando... Pode remover da tomada em 30 segundos."

@app.route('/salvar_msg', methods=['POST'])
def salvar_msg():
    msg = request.form.get('msg', '')
    config = ler_config()
    config['msg_custom'] = msg
    salvar_config(config)
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
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
