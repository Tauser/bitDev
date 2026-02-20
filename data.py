import requests
import socket
import json
import os
import time
import threading
import config as cfg
from rgbmatrix import graphics

JSON_PATH = os.path.join(cfg.BASE_DIR, 'user_config.json')

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
    'printer': {'state': 'OFF', 'progress': 0, 'ext_actual': 0, 'ext_target': 0, 'bed_actual': 0, 'bed_target': 0, 'z_height': 0, 'fan_speed': 0, 'print_duration': 0, 'total_duration': 0, 'filename': '', 'homed_axes': '', 'print_speed': 0, 'message': '', 'is_moving': False, 'sensors': {}, 'qgl_applied': False, 'position': [0,0,0], 'stats': {'total_time': 0, 'total_filament': 0, 'total_jobs': 0}},
    'printer_name': 'VORON 2.4',
    'wifi_signal': 0,
    'weather': {'temp': 0, 'min': 0, 'max': 0, 'humidity': 0, 'wind': 0, 'code': 0, 'uv': 0, 'feels_like': 0, 'hourly_temps': [], 'is_day': 1, 'pop': 0}
}

_printer_cached_url = None
_printer_fail_count = 0
_printer_query_keys = []
_printer_current_file = None
_printer_file_metadata = {}

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
                
                if config.get('manual_coords'):
                    dados['lat'] = config.get('lat')
                    dados['lon'] = config.get('lon')
                    dados['manual_coords'] = True
                    dados['using_manual'] = True
                else:
                    dados['manual_coords'] = False
                    if dados.get('using_manual'):
                        dados.pop('lat', None)
                        dados.pop('lon', None)
                        dados['_cached_city'] = None
                        dados['using_manual'] = False
        except: pass
    return alterou_moedas

def check_internet():
    try:
        requests.get("http://clients3.google.com/generate_204", timeout=2)
        return True
    except:
        return False

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
        s.close()
    except:
        IP = "127.0.0.1"
    return IP

def get_wifi_signal():
    try:
        with open("/proc/net/wireless", "r") as f:
            for line in f:
                if "wlan0" in line:
                    return float(line.split()[3].replace('.', ''))
    except: pass
    return 0

def save_debug_info():
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
    if color is None: color = cfg.C_WHITE
    expire = time.time() + duration
    dados['notifications'].append({'msg': msg, 'expires': expire, 'color': color})

def get_active_notification():
    now = time.time()
    dados['notifications'] = [n for n in dados['notifications'] if n['expires'] > now]
    if dados['notifications']:
        return dados['notifications'][-1]
    return None

def fetch_btc_only():
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
    global dados
    try:
        r = requests.get("https://economia.awesomeapi.com.br/last/USD-BRL", timeout=2).json()
        dados['usdtbrl'] = float(r['USDBRL']['bid'])
    except: pass

    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=2).json()
        dados['fg_val'] = int(r['data'][0]['value'])
        dados['wifi_signal'] = get_wifi_signal()
    except: pass

def ler_temperatura():
    global dados
    cidade = dados.get('cidade', 'Sao_Paulo')
    
    if not dados.get('manual_coords', False):
        if dados.get('_cached_city') != cidade or 'lat' not in dados:
            try:
                cidade_query = cidade.replace('_', ' ') # Troca Sao_Paulo por Sao Paulo
                geo_url = "https://geocoding-api.open-meteo.com/v1/search"
                params = {'name': cidade_query, 'count': 1, 'language': 'pt', 'format': 'json'}
                
                r = requests.get(geo_url, params=params, timeout=3)
                geo_data = r.json()
                
                if geo_data.get('results'):
                    dados['lat'] = geo_data['results'][0]['latitude']
                    dados['lon'] = geo_data['results'][0]['longitude']
                    dados['_cached_city'] = cidade
            except: pass

    if 'lat' in dados:
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                'latitude': dados['lat'], 
                'longitude': dados['lon'], 
                'current': 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature,is_day',
                'hourly': 'uv_index,temperature_2m',
                'daily': 'temperature_2m_max,temperature_2m_min,precipitation_probability_max',
                'timezone': 'auto'
            }
            r = requests.get(url, params=params, timeout=3)
            weather_data = r.json()
            
            utc_offset = weather_data.get('utc_offset_seconds', 0)
            local_hour = time.gmtime(time.time() + utc_offset).tm_hour
            
            curr = weather_data.get('current', {})
            daily = weather_data.get('daily', {})
            hourly = weather_data.get('hourly', {})
            
            if curr:
                t = int(round(curr['temperature_2m']))
                dados['temp'] = str(t)
                dados['weather']['temp'] = t
                dados['weather']['humidity'] = curr['relative_humidity_2m']
                dados['weather']['wind'] = curr['wind_speed_10m']
                dados['weather']['code'] = curr['weather_code']
                dados['weather']['feels_like'] = int(round(curr.get('apparent_temperature', t)))
                dados['weather']['is_day'] = curr.get('is_day', 1)
            
            if hourly:
                if 'uv_index' in hourly:
                    idx = max(0, min(23, local_hour))
                    dados['weather']['uv'] = hourly['uv_index'][idx]
                if 'temperature_2m' in hourly:
                    dados['weather']['hourly_temps'] = hourly['temperature_2m'][local_hour:local_hour+12]
            
            if daily:
                dados['weather']['min'] = int(round(daily['temperature_2m_min'][0]))
                dados['weather']['max'] = int(round(daily['temperature_2m_max'][0]))
                dados['weather']['pop'] = int(round(daily['precipitation_probability_max'][0]))
        except: pass

def fetch_stocks():
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

    get_ticker('^BVSP', 'ibov', 'ibov_var')
    get_ticker('^GSPC', 'sp500', 'sp500_var')
    get_ticker('^IXIC', 'nasdaq', 'nasdaq_var')

def fetch_printer_data():
    global dados, _printer_cached_url, _printer_fail_count, _printer_query_keys, _printer_current_file, _printer_file_metadata
    raw_ip = dados.get('printer_ip', '').strip()
    
    if not raw_ip: 
        dados['printer']['state'] = 'OFFLINE'
        dados['status']['printer'] = False
        return

    ip = raw_ip.replace("http://", "").replace("https://", "").rstrip("/")
    
    candidates = []
    if _printer_cached_url and ip in _printer_cached_url:
        candidates.append(_printer_cached_url)
    
    defaults = [f"http://{ip}", f"http://{ip}:7125"]
    if ":" in ip: defaults = [f"http://{ip}"]
    
    for u in defaults:
        if u not in candidates: candidates.append(u)

    success = False
    r_json = None
    
    for base_url in candidates:
        try:
            if not _printer_query_keys:
                try:
                    r_list = requests.get(f"{base_url}/printer/objects/list", timeout=2)
                    if r_list.status_code == 200:
                        all_objs = r_list.json().get('result', {}).get('objects', [])
                        keys = ['print_stats', 'display_status', 'extruder', 'heater_bed', 'fan', 'toolhead', 'gcode_move', 'quad_gantry_level']
                        for obj in all_objs:
                            if obj.startswith('temperature_sensor') or \
                               obj.startswith('temperature_fan') or \
                               obj.startswith('heater_generic'):
                                keys.append(obj)
                        _printer_query_keys = keys
                except: pass

            q_keys = _printer_query_keys if _printer_query_keys else ['print_stats', 'display_status', 'extruder', 'heater_bed', 'fan', 'toolhead', 'gcode_move', 'quad_gantry_level']
            
            url = f"{base_url}/printer/objects/query?" + "&".join(q_keys)
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                try:
                    val = r.json()
                    if 'result' in val:
                        r_json = val
                        success = True
                        _printer_cached_url = base_url
                        _printer_fail_count = 0
                        break
                except: pass
        except: continue
    
    if not success or not r_json:
        _printer_fail_count += 1
        if _printer_cached_url: _printer_cached_url = None
        _printer_query_keys = []

        if _printer_fail_count >= 5:
            dados['printer']['state'] = 'OFFLINE'
            dados['status']['printer'] = False
        return

    try:
        res = r_json.get('result', {}).get('status', {})
        p_stats = res.get('print_stats', {})
        disp    = res.get('display_status', {})
        ext     = res.get('extruder', {})
        bed     = res.get('heater_bed', {})
        fan     = res.get('fan', {})
        tool    = res.get('toolhead', {})
        move    = res.get('gcode_move', {})
        
        filename = p_stats.get('filename', '')
        if filename and filename != _printer_current_file:
            _printer_current_file = filename
            _printer_file_metadata = {}
            try:
                meta_url = f"{_printer_cached_url}/server/files/metadata?filename={filename}"
                r_meta = requests.get(meta_url, timeout=1)
                if r_meta.status_code == 200:
                    _printer_file_metadata = r_meta.json().get('result', {})
            except: pass
        elif not filename:
            _printer_current_file = None
            _printer_file_metadata = {}

        p_data = dados['printer']
        current_state = p_stats.get('state', 'error')
        last_state = p_data.get('_last_state', '')
        
        if last_state and current_state != last_state:
            if current_state == 'printing' and last_state != 'paused':
                fname = p_stats.get('filename', '')
                add_notification(f"Imprimindo: {fname}", cfg.C_TEAL, 10)
            elif current_state == 'complete':
                add_notification("Impressao Finalizada!", cfg.C_GREEN, 60)
            elif current_state == 'error':
                add_notification("Erro na Impressora!", cfg.C_RED, 60)
        
        p_data['_last_state'] = current_state

        p_data['state']      = current_state
        p_data['progress']   = float(disp.get('progress', 0)) * 100
        p_data['filename']   = p_stats.get('filename', '')
        p_data['message']    = str(disp.get('message') or '')
        p_data['print_duration'] = p_stats.get('print_duration', 0)
        p_data['total_duration'] = p_stats.get('total_duration', 0)
        
        info = p_stats.get('info') or {}
        current_layer = info.get('current_layer')
        total_layer = info.get('total_layer')
        
        if (not current_layer or not total_layer) and _printer_file_metadata:
            z_height = (tool.get('position') or [0,0,0])[2]
            layer_h = _printer_file_metadata.get('layer_height', 0)
            obj_h = _printer_file_metadata.get('object_height', 0)
            first_layer_h = _printer_file_metadata.get('first_layer_height', layer_h)
            
            if layer_h > 0:
                if not total_layer and obj_h > 0:
                    total_layer = int(obj_h / layer_h)
                
                if not current_layer and z_height > 0:
                    if z_height <= first_layer_h:
                        current_layer = 1
                    else:
                        current_layer = 1 + int((z_height - first_layer_h) / layer_h)
        
        p_data['layer'] = int(current_layer or 0)
        p_data['total_layers'] = int(total_layer or 0)
        
        p_data['ext_actual'] = ext.get('temperature', 0)
        p_data['ext_target'] = ext.get('target', 0)
        p_data['bed_actual'] = bed.get('temperature', 0)
        p_data['bed_target'] = bed.get('target', 0)
        
        p_data['ext_power']  = int((ext.get('power') or 0) * 100)
        p_data['bed_power']  = int((bed.get('power') or 0) * 100)
        p_data['speed_factor'] = int((move.get('speed_factor') or 1) * 100)
        p_data['flow_factor'] = int((move.get('extrude_factor') or 1) * 100)
        
        p_data['fan_speed']  = int((fan.get('speed') or 0) * 100)
        p_data['z_height']   = (tool.get('position') or [0,0,0])[2]
        p_data['homed_axes'] = (tool.get('homed_axes') or '')
        p_data['print_speed'] = int(move.get('speed') or 0)
        p_data['position']   = tool.get('position', [0,0,0])
        p_data['qgl_applied'] = res.get('quad_gantry_level', {}).get('applied', False)

        p_data['sensors'] = {}
        for key, val in res.items():
            if key.startswith('temperature_sensor'):
                name = key.replace('temperature_sensor ', '')
                p_data['sensors'][name] = val.get('temperature', 0)
            elif key.startswith('temperature_fan'):
                name = key.replace('temperature_fan ', '')
                p_data['sensors'][name] = val.get('temperature', 0)
            elif key.startswith('heater_generic'):
                name = key.replace('heater_generic ', '')
                p_data['sensors'][name] = val.get('temperature', 0)
        
        raw_pos = tool.get('position', [0,0,0])
        current_xyz = raw_pos[:3]
        last_xyz = p_data.get('_last_xyz', current_xyz)
        
        p_data['is_moving'] = any(abs(c - l) > 0.5 for c, l in zip(current_xyz, last_xyz))
        p_data['_last_xyz'] = current_xyz
        
        try:
            h_url = f"{base_url}/server/history/totals"
            h_r = requests.get(h_url, timeout=1)
            if h_r.status_code == 200:
                totals = h_r.json().get('result', {}).get('job_totals', {})
                p_data['stats']['total_time'] = totals.get('total_time', 0)
                p_data['stats']['total_filament'] = totals.get('total_filament_used', 0)
                p_data['stats']['total_jobs'] = totals.get('total_jobs', 0)
        except: pass

        dados['status']['printer'] = True
        
    except Exception as e:
        print(f"Erro Parse Klipper: {e}")
        # Nao marca offline imediatamente por erro de parse, espera o contador

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