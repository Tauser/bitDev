import requests
import socket
import json
import os
import time
import threading
import config as cfg
from rgbmatrix import graphics

JSON_PATH = os.path.join(cfg.BASE_DIR, 'moedas.json')

dados = {
    'temp': '0',
    'brilho': 70,
    'fg_val': 50,
    'usdtbrl': 5.00,
    'conexao': True,
    'bitcoin': {'usd': 0, 'brl': 0, 'change': 0},
    'secondary': [],
    'moedas_ativas': ['BTC', 'ETH', 'SOL'],
    'cidade': 'Sao_Paulo',
    'msg_custom': '',
    'notifications': [],
    'status': {'btc': False, 'stocks': False, 'printer': False},
    'stocks': {'ibov': 0, 'ibov_var': 0, 'sp500': 0, 'sp500_var': 0, 'nasdaq': 0, 'nasdaq_var': 0},
    'printer': {'state': 'OFF', 'progress': 0, 'ext_actual': 0, 'ext_target': 0, 'bed_actual': 0, 'bed_target': 0, 'z_height': 0, 'fan_speed': 0, 'print_duration': 0, 'total_duration': 0, 'filename': '', 'homed_axes': '', 'print_speed': 0, 'message': '', 'is_moving': False, 'sensors': {}, 'qgl_applied': False, 'position': [0,0,0]},
    'printer_name': 'VORON 2.4'
}

def get_color(symbol):
    sym = symbol.upper()
    if sym == 'BTC': return cfg.C_ORANGE
    if sym == 'ETH': return cfg.C_BLUE
    if sym == 'SOL': return graphics.Color(153, 69, 255)
    if sym == 'ADA': return graphics.Color(0, 51, 173)
    if sym == 'DOGE': return cfg.C_GOLD
    if sym == 'XRP': return cfg.C_WHITE
    if sym == 'BNB': return cfg.C_YELLOW
    return cfg.C_TEAL

def carregar_config():
    global dados
    alterou_moedas = False
    config = None
    
    try:
        if os.path.exists(JSON_PATH):
            with open(JSON_PATH, 'r') as f:
                config = json.load(f)
    except:
        print("Config principal corrompida ou ilegível. Tentando backup...")
        try:
            bak_path = JSON_PATH + ".bak"
            if os.path.exists(bak_path):
                with open(bak_path, 'r') as f: config = json.load(f)
        except: pass

    if config:
        try:
                dados['brilho'] = int(config.get('brilho', 70))
                dados['cidade'] = config.get('cidade', 'Sao_Paulo')
                dados['printer_ip'] = config.get('printer_ip', '')
                dados['printer_name'] = config.get('printer_name', 'VORON 2.4')
                dados['msg_custom'] = config.get('msg_custom', '')
                
                raw_list = config.get('secundarias', [])
                if isinstance(raw_list, list):
                    clean_list = []
                    for item in raw_list:
                        clean = item.replace('USDT', '').replace('usdt', '')
                        if clean != 'BTC': 
                            clean_list.append(clean)
                    
                    if clean_list != dados['moedas_ativas']:
                        print(f"--> Config: {clean_list}")
                        dados['moedas_ativas'] = clean_list
                        alterou_moedas = True
        except: pass
    return alterou_moedas

def check_internet():
    """Verifica se há conexão real com a internet (Google)"""
    try:
        requests.get("http://clients3.google.com/generate_204", timeout=2)
        return True
    except:
        return False

def get_local_ip():
    """Retorna o IP local da máquina"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
        s.close()
    except:
        IP = "127.0.0.1"
    return IP

def save_debug_info():
    """Salva status na partição de boot para leitura no Windows"""
    try:
        if os.path.exists("/boot"):
            path = "/boot/bitdev_status.txt"
            ip = get_local_ip()
            wifi_status = "CONECTADO" if ip != "127.0.0.1" else "DESCONECTADO"
            internet = "OK" if dados.get('conexao') else "SEM INTERNET"
            
            with open(path, "w") as f:
                f.write("--- BITDEV MONITOR STATUS ---\n")
                f.write(f"Atualizado em: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"IP Local: {ip}\n")
                f.write(f"Wi-Fi: {wifi_status}\n")
                f.write(f"Internet: {internet}\n")
                
                try:
                    files = os.listdir("/boot")
                    if "network-config" in files: f.write("Aviso: 'network-config' detectado (pode ser ignorado).\n")
                    if "wpa_supplicant.conf" in files: f.write("ALERTA: 'wpa_supplicant.conf' ainda presente (nao processado/erro de sintaxe).\n")
                except: pass
                
                f.flush()
                os.fsync(f.fileno())
    except Exception as e:
        print(f"Erro ao salvar debug: {e}")

def add_notification(msg, color=None, duration=15):
    """Adiciona uma notificação temporária ao rodapé"""
    if color is None: color = cfg.C_WHITE
    expire = time.time() + duration
    dados['notifications'].append({'msg': msg, 'expires': expire, 'color': color})

def get_active_notification():
    """Retorna a notificação mais recente e limpa as expiradas"""
    now = time.time()
    dados['notifications'] = [n for n in dados['notifications'] if n['expires'] > now]
    if dados['notifications']:
        return dados['notifications'][-1]
    return None

def fetch_btc_only():
    """Busca APENAS o Bitcoin (Muito Rápido)"""
    global dados
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
        r = requests.get(url, timeout=5).json()
        
        price = float(r['lastPrice'])
        change = float(r['priceChangePercent'])
        
        dados['bitcoin']['usd'] = price
        dados['bitcoin']['change'] = change
        dados['bitcoin']['brl'] = price * dados['usdtbrl']
        dados['conexao'] = True
        dados['status']['btc'] = True
    except Exception as e:
        print(f"Erro ao buscar BTC: {e}")
        dados['status']['btc'] = False
        
        if check_internet():
            dados['conexao'] = True
        else:
            dados['conexao'] = False

def fetch_secondary_coins():
    """Busca as outras moedas (Mais Lento)"""
    global dados
    temp_list = []
    
    for symbol in dados['moedas_ativas']:
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}USDT"
            r = requests.get(url, timeout=2).json()
            
            temp_list.append({
                's': symbol.upper(),
                'p': float(r['lastPrice']),
                'c': float(r['priceChangePercent']),
                'col': get_color(symbol)
            })
        except: pass
    
    dados['secondary'] = temp_list

def fetch_extras():
    """Dólar e Fear & Greed"""
    global dados
    try:
        r = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL", timeout=2).json()
        dados['usdtbrl'] = float(r['USDBRL']['bid'])
    except: pass

    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=2).json()
        dados['fg_val'] = int(r['data'][0]['value'])
    except: pass

def ler_temperatura():
    """Clima da Cidade"""
    global dados
    cidade = dados.get('cidade', 'Sao_Paulo')
    try:
        url = f"https://wttr.in/{cidade}?format=%t"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            dados['temp'] = r.text.strip().replace("+", "").replace("°C", "").replace("C", "")
    except: pass

def fetch_stocks():
    """Busca IBOVESPA e S&P 500 (Yahoo Finance)"""
    global dados
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    def get_ticker(symbol, key_price, key_var):
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            r = requests.get(url, headers=headers, timeout=2).json()
            meta = r['chart']['result'][0]['meta']
            price = meta['regularMarketPrice']
            prev = meta['chartPreviousClose']
            dados['stocks'][key_price] = price
            dados['stocks'][key_var] = ((price - prev) / prev) * 100
            dados['status']['stocks'] = True
        except: pass

    get_ticker('^BVSP', 'ibov', 'ibov_var')   # Ibovespa
    get_ticker('^GSPC', 'sp500', 'sp500_var') # S&P 500
    get_ticker('^IXIC', 'nasdaq', 'nasdaq_var') # Nasdaq (Tech)

def fetch_printer_data():
    """Busca dados do Klipper/Moonraker"""
    global dados
    ip = dados.get('printer_ip')
    if not ip: 
        dados['printer']['state'] = 'OFFLINE'
        dados['status']['printer'] = False
        return

    try:
        sensor_query = "&quad_gantry_level&temperature_sensor CHAMBER&temperature_sensor EBB_SB2009&temperature_sensor OCTOPUS_PRO&temperature_sensor RASPIBERRY_4"
        url = f"http://{ip}/printer/objects/query?print_stats&display_status&extruder&heater_bed&fan&toolhead&gcode_move{sensor_query}"
        r = requests.get(url, timeout=2).json()
        
        res = r['result']['status']
        
        disp = res.get('display_status', {})
        
        p_data = dados['printer']
        
        current_state = res['print_stats']['state']
        last_state = p_data.get('_last_state', '')
        
        if last_state and current_state != last_state:
            if current_state == 'printing' and last_state != 'paused':
                fname = res['print_stats']['filename']
                add_notification(f"Imprimindo: {fname}", cfg.C_TEAL, 10)
            elif current_state == 'complete':
                add_notification("Impressao Finalizada!", cfg.C_GREEN, 60)
            elif current_state == 'error':
                add_notification("Erro na Impressora!", cfg.C_RED, 60)
        
        p_data['_last_state'] = current_state

        p_data['state']      = res['print_stats']['state']
        p_data['progress']   = float(disp.get('progress', 0)) * 100
        p_data['filename']   = res['print_stats']['filename']
        p_data['message']    = str(disp.get('message') or '')
        p_data['print_duration'] = res['print_stats'].get('print_duration', 0)
        p_data['total_duration'] = res['print_stats'].get('total_duration', 0)
        
        p_data['ext_actual'] = res['extruder']['temperature']
        p_data['ext_target'] = res['extruder']['target']
        p_data['bed_actual'] = res['heater_bed']['temperature']
        p_data['bed_target'] = res['heater_bed']['target']
        
        p_data['ext_power']  = int(res['extruder'].get('power', 0) * 100)
        p_data['bed_power']  = int(res['heater_bed'].get('power', 0) * 100)
        p_data['speed_factor'] = int(res.get('gcode_move', {}).get('speed_factor', 1) * 100)
        p_data['flow_factor'] = int(res.get('gcode_move', {}).get('extrude_factor', 1) * 100)
        
        p_data['fan_speed']  = int(res.get('fan', {}).get('speed', 0) * 100)
        p_data['z_height']   = res.get('toolhead', {}).get('position', [0,0,0])[2]
        p_data['homed_axes'] = res.get('toolhead', {}).get('homed_axes', '')
        p_data['print_speed'] = int(res.get('gcode_move', {}).get('speed', 0))
        p_data['position']   = res.get('toolhead', {}).get('position', [0,0,0])
        p_data['qgl_applied'] = res.get('quad_gantry_level', {}).get('applied', False)

        p_data['sensors'] = {}
        for key, val in res.items():
            if key.startswith('temperature_sensor'):
                name = key.replace('temperature_sensor ', '')
                p_data['sensors'][name] = val.get('temperature', 0)
        
        raw_pos = res.get('toolhead', {}).get('position', [0,0,0])
        current_xyz = raw_pos[:3]
        last_xyz = p_data.get('_last_xyz', current_xyz)
        
        p_data['is_moving'] = any(abs(c - l) > 0.5 for c, l in zip(current_xyz, last_xyz))
        p_data['_last_xyz'] = current_xyz
        
        dados['status']['printer'] = True
        
    except: 
        dados['printer']['state'] = 'OFFLINE'
        dados['status']['printer'] = False

def loop_atualizacao(matrix):
    print(">> Iniciando Coleta de Dados Prioritária...")
    
    carregar_config()
    
    fetch_btc_only()
    
    fetch_extras()
    threading.Thread(target=lambda: (ler_temperatura(), fetch_stocks(), fetch_printer_data(), fetch_secondary_coins(), save_debug_info())).start()
    
    timer_secundarias = 0
    timer_lento = 0
    
    while True:
        time.sleep(2)
        
        if carregar_config():
            fetch_secondary_coins()
            timer_secundarias = 0
            
        fetch_btc_only()
        fetch_printer_data()
        
        timer_secundarias += 2
        timer_lento += 2
        
        if timer_secundarias >= 10:
            fetch_secondary_coins()
            timer_secundarias = 0
            
        if timer_lento >= 60:
            fetch_extras()
            ler_temperatura()
            fetch_stocks()
            timer_lento = 0

def iniciar_thread(matrix):
    t = threading.Thread(target=loop_atualizacao, args=(matrix,))
    t.daemon = True
    t.start()