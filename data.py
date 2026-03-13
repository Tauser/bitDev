import datetime
import os
import socket
import threading
import time
from functools import wraps

import config as cfg

from infra.http_client import get_http_client
from infra.logging_config import get_logger
from services.config_service import read_config, write_config
from providers import agenda as agenda_provider
from providers import crypto as crypto_provider
from providers import stocks as stocks_provider
from providers import weather as weather_provider
from providers.printer import PrinterProvider

logger = get_logger(__name__)

try:
    from icalendar import Calendar

    ICAL_AVAILABLE = True
except ImportError:
    logger.warning("op=icalendar_import status=missing_library detail='icalendar nao encontrado; execute bash install.sh'")
    Calendar = None
    ICAL_AVAILABLE = False
except Exception as e:
    logger.warning("op=icalendar_import status=failed reason=%s", e)
    Calendar = None
    ICAL_AVAILABLE = False

JSON_PATH = os.path.join(cfg.BASE_DIR, "user_config.json")
SNAPSHOT_CACHE_PATH = os.path.join(cfg.BASE_DIR, ".runtime_snapshot.json")
SNAPSHOT_CACHE_SAVE_INTERVAL_S = 30
SNAPSHOT_CACHE_MAX_AGE_S = 7 * 24 * 3600

TTL_POLICY_S = {
    "btc": 20,
    "secondary": 60,
    "extras": 300,
    "stocks": 900,
    "weather": 1800,
    "agenda": 3600,
    "printer": 30,
}

_CACHE_FIELDS = [
    "temp",
    "usdtbrl",
    "conexao",
    "bitcoin",
    "agenda",
    "secondary",
    "status",
    "stocks",
    "printer",
    "wifi_signal",
    "weather",
    "freshness",
]

http_client = get_http_client()
printer_provider = PrinterProvider()

dados = {
    "temp": "0",
    "brilho": 70,
    "fg_val": 50,
    "gif_speed": 0.1,
    "usdtbrl": 5.00,
    "conexao": True,
    "bitcoin": {"usd": 0, "brl": 0, "change": 0},
    "agenda": [],
    "agenda_url": "",
    "secondary": [],
    "moedas_ativas": ["BTC", "ETH", "SOL"],
    "cidade": "Sao_Paulo",
    "msg_custom": "",
    "notifications": [],
    "status": {"btc": False, "stocks": False, "printer": False},
    "stocks": {"ibov": 0, "ibov_var": 0, "sp500": 0, "sp500_var": 0, "nasdaq": 0, "nasdaq_var": 0},
    "printer": {
        "state": "OFF",
        "progress": 0,
        "ext_actual": 0,
        "ext_target": 0,
        "bed_actual": 0,
        "bed_target": 0,
        "z_height": 0,
        "fan_speed": 0,
        "print_duration": 0,
        "total_duration": 0,
        "filename": "",
        "homed_axes": "",
        "print_speed": 0,
        "message": "",
        "is_moving": False,
        "sensors": {},
        "qgl_applied": False,
        "position": [0, 0, 0],
        "stats": {"total_time": 0, "total_filament": 0, "total_jobs": 0},
    },
    "printer_name": "VORON 2.4",
    "wifi_signal": 0,
    "weather": {
        "temp": 0,
        "min": 0,
        "max": 0,
        "humidity": 0,
        "wind": 0,
        "code": 0,
        "uv": 0,
        "feels_like": 0,
        "hourly_temps": [],
        "is_day": 1,
        "pop": 0,
    },
    "freshness": {
        "ttl_s": dict(TTL_POLICY_S),
        "last_ok": {},
        "age_s": {},
        "stale": {},
        "has_stale": False,
        "offline_since": None,
    },
}

STATE_LOCK = threading.RLock()
_state_snapshot = {}
_collector_thread = None
_collector_started_at = 0.0
_collector_last_tick = 0.0
_last_snapshot_persist_at = 0.0
_snapshot_dirty = False

_PROVIDER_KEYS = ("btc", "secondary", "extras", "weather", "agenda", "stocks", "printer")
_provider_stats = {
    key: {
        "attempts": 0,
        "success": 0,
        "errors": 0,
        "last_ok": None,
        "last_error": "",
        "last_duration_ms": 0,
    }
    for key in _PROVIDER_KEYS
}


def _record_provider_result(name, started_at, success, exc=None):
    stats = _provider_stats.setdefault(
        name,
        {
            "attempts": 0,
            "success": 0,
            "errors": 0,
            "last_ok": None,
            "last_error": "",
            "last_duration_ms": 0,
        },
    )
    stats["attempts"] += 1
    stats["last_duration_ms"] = int(max(0, (time.time() - started_at) * 1000))
    if success:
        stats["success"] += 1
        stats["last_ok"] = time.time()
        stats["last_error"] = ""
    else:
        stats["errors"] += 1
        if exc is not None:
            stats["last_error"] = str(exc)[:180]


def _run_provider(name, fn):
    started = time.time()
    try:
        result = fn()
        _record_provider_result(name, started, True)
        return result
    except Exception as exc:
        _record_provider_result(name, started, False, exc)
        logger.warning("op=provider_fetch status=failed provider=%s reason=%s", name, exc)
        return None


def _snapshot_value(value):
    if isinstance(value, dict):
        return {k: _snapshot_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_snapshot_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_snapshot_value(v) for v in value)

    # rgbmatrix Color objects are not JSON-serializable; store as RGB tuple.
    if hasattr(value, "red") and hasattr(value, "green") and hasattr(value, "blue"):
        try:
            return (int(value.red), int(value.green), int(value.blue))
        except Exception:
            return (0, 0, 0)

    return value


def _mark_data_ok_locked(key):
    freshness = dados.setdefault("freshness", {})
    last_ok = freshness.setdefault("last_ok", {})
    last_ok[key] = time.time()

    global _snapshot_dirty
    _snapshot_dirty = True


def _update_staleness_locked():
    now = time.time()
    freshness = dados.setdefault("freshness", {})
    freshness["ttl_s"] = dict(TTL_POLICY_S)
    last_ok = freshness.setdefault("last_ok", {})

    age_s = {}
    stale = {}

    for key, ttl in TTL_POLICY_S.items():
        last = last_ok.get(key)
        if not last:
            age_s[key] = None
            stale[key] = True
            continue

        age = max(0, int(now - float(last)))
        age_s[key] = age
        stale[key] = age > ttl

    if dados.get("conexao", True):
        freshness["offline_since"] = None
    elif freshness.get("offline_since") is None:
        freshness["offline_since"] = now

    freshness["age_s"] = age_s
    freshness["stale"] = stale
    freshness["has_stale"] = any(stale.values())


def _refresh_snapshot_locked():
    global _state_snapshot
    _update_staleness_locked()
    _state_snapshot = _snapshot_value(dados)


def _snapshot_payload_locked():
    payload = {"saved_at": time.time(), "state": {}}
    for key in _CACHE_FIELDS:
        if key in dados:
            payload["state"][key] = _snapshot_value(dados[key])
    return payload


def _persist_snapshot_if_needed(force=False):
    global _last_snapshot_persist_at, _snapshot_dirty

    now = time.time()
    if not force:
        if not _snapshot_dirty:
            return
        if (now - _last_snapshot_persist_at) < SNAPSHOT_CACHE_SAVE_INTERVAL_S:
            return

    with STATE_LOCK:
        payload = _snapshot_payload_locked()
        try:
            write_config(
                SNAPSHOT_CACHE_PATH,
                payload,
                backup_path=f"{SNAPSHOT_CACHE_PATH}.bak",
                logger=logger,
                file_mode=0o640,
            )
            _last_snapshot_persist_at = now
            _snapshot_dirty = False
        except Exception as exc:
            logger.warning("op=snapshot_persist status=failed reason=%s", exc)


def _load_cached_snapshot():
    payload = read_config(
        SNAPSHOT_CACHE_PATH,
        default=None,
        backup_path=f"{SNAPSHOT_CACHE_PATH}.bak",
        logger=logger,
    )
    if not isinstance(payload, dict):
        return False

    saved_at = payload.get("saved_at")
    if saved_at:
        try:
            age = time.time() - float(saved_at)
            if age > SNAPSHOT_CACHE_MAX_AGE_S:
                return False
        except (TypeError, ValueError):
            return False

    state = payload.get("state")
    if not isinstance(state, dict):
        return False

    with STATE_LOCK:
        for key in _CACHE_FIELDS:
            if key in state:
                dados[key] = state[key]
        _refresh_snapshot_locked()

    logger.info("op=snapshot_load status=ok source=%s", SNAPSHOT_CACHE_PATH)
    return True


def state_write(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with STATE_LOCK:
            result = func(*args, **kwargs)
            _refresh_snapshot_locked()
            return result

    return wrapper


def get_state_snapshot():
    return _state_snapshot


def get_stale_info(keys=None):
    snapshot = get_state_snapshot()
    freshness = snapshot.get("freshness", {})
    stale_map = freshness.get("stale", {})
    age_s_map = freshness.get("age_s", {})

    if keys:
        stale_keys = [k for k in keys if stale_map.get(k)]
    else:
        stale_keys = [k for k, v in stale_map.items() if v]

    if not stale_keys:
        return {"is_stale": False, "keys": [], "max_age_s": 0, "text": ""}

    max_age = 0
    for key in stale_keys:
        age = age_s_map.get(key)
        if isinstance(age, int):
            max_age = max(max_age, age)

    if max_age >= 3600:
        text = f"stale {max_age // 3600}h"
    elif max_age >= 60:
        text = f"stale {max_age // 60}m"
    else:
        text = f"stale {max_age}s"

    return {"is_stale": True, "keys": stale_keys, "max_age_s": max_age, "text": text}


_refresh_snapshot_locked()


def get_color(symbol):
    return crypto_provider.get_color(symbol, cfg)


@state_write
def carregar_config():
    alterou_moedas = False
    config = read_config(JSON_PATH, default=None, backup_path=f"{JSON_PATH}.bak", logger=logger)

    if config:
        try:
            dados["brilho"] = int(config.get("brilho", 70))
            dados["cidade"] = config.get("cidade", "Sao_Paulo")
            dados["printer_ip"] = config.get("printer_ip", "")
            dados["printer_name"] = config.get("printer_name", "VORON 2.4")
            dados["msg_custom"] = config.get("msg_custom", "")
            dados["modo_noturno"] = config.get("modo_noturno", False)
            dados["gif_speed"] = float(config.get("gif_speed", 0.1))
            dados["agenda_url"] = config.get("agenda_url", "")

            raw_list = config.get("secundarias", [])
            if isinstance(raw_list, list):
                clean_list = []
                for item in raw_list:
                    clean = item.replace("USDT", "").replace("usdt", "")
                    if clean != "BTC":
                        clean_list.append(clean)

                if clean_list != dados["moedas_ativas"]:
                    logger.info("op=carregar_config status=coins_updated moedas=%s", clean_list)
                    dados["moedas_ativas"] = clean_list
                    alterou_moedas = True

            if config.get("manual_coords"):
                dados["lat"] = config.get("lat")
                dados["lon"] = config.get("lon")
                dados["manual_coords"] = True
                dados["using_manual"] = True
            else:
                dados["manual_coords"] = False
                if dados.get("using_manual"):
                    dados.pop("lat", None)
                    dados.pop("lon", None)
                    dados["_cached_city"] = None
                    dados["using_manual"] = False
        except Exception:
            pass
    return alterou_moedas


def check_internet():
    try:
        http_client.get("http://clients3.google.com/generate_204", timeout=2)
        return True
    except Exception:
        return False


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 1))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "127.0.0.1"
    return ip


def get_wifi_signal():
    try:
        with open("/proc/net/wireless", "r") as f:
            for line in f:
                if "wlan0" in line:
                    return float(line.split()[3].replace(".", ""))
    except Exception:
        pass
    return 0


def save_debug_info():
    try:
        if os.path.exists("/boot"):
            path = "/boot/bitdev_status.txt"
            ip = get_local_ip()
            wifi_status = "CONECTADO" if ip != "127.0.0.1" else "DESCONECTADO"
            internet = "OK" if dados.get("conexao") else "SEM INTERNET"

            with open(path, "w") as f:
                f.write("--- BITDEV MONITOR STATUS ---\n")
                f.write(f"Atualizado em: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"IP Local: {ip}\n")
                f.write(f"Wi-Fi: {wifi_status}\n")
                f.write(f"Internet: {internet}\n")

                try:
                    files = os.listdir("/boot")
                    if "network-config" in files:
                        f.write("Aviso: 'network-config' detectado (pode ser ignorado).\n")
                    if "wpa_supplicant.conf" in files:
                        f.write("ALERTA: 'wpa_supplicant.conf' ainda presente (nao processado/erro de sintaxe).\n")
                except Exception:
                    pass

                f.flush()
                os.fsync(f.fileno())
    except Exception as e:
        logger.warning("op=save_debug_info status=failed reason=%s", e)


@state_write
def add_notification(msg, color=None, duration=15):
    if color is None:
        color = cfg.C_WHITE
    expire = time.time() + duration
    dados["notifications"].append({"msg": msg, "expires": expire, "color": color})


@state_write
def get_active_notification():
    now = time.time()
    dados["notifications"] = [n for n in dados["notifications"] if n["expires"] > now]
    if dados["notifications"]:
        return dados["notifications"][-1]
    return None


@state_write
def fetch_btc_only():
    _run_provider("btc", lambda: crypto_provider.fetch_btc_only(dados, http_client, check_internet, logger))
    if dados["status"].get("btc") and dados.get("bitcoin", {}).get("usd", 0) > 0:
        _mark_data_ok_locked("btc")


@state_write
def fetch_secondary_coins():
    _run_provider("secondary", lambda: crypto_provider.fetch_secondary_coins(dados, http_client, get_color))
    if dados.get("secondary"):
        _mark_data_ok_locked("secondary")


@state_write
def fetch_extras():
    before = (dados.get("usdtbrl"), dados.get("fg_val"), dados.get("wifi_signal"))
    _run_provider("extras", lambda: crypto_provider.fetch_extras(dados, http_client, get_wifi_signal))
    after = (dados.get("usdtbrl"), dados.get("fg_val"), dados.get("wifi_signal"))
    if after != before:
        _mark_data_ok_locked("extras")


@state_write
def ler_temperatura():
    before = _snapshot_value(dados.get("weather", {}))
    _run_provider("weather", lambda: weather_provider.fetch_weather(dados, http_client))
    after = dados.get("weather", {})
    if after and after != before:
        _mark_data_ok_locked("weather")


@state_write
def fetch_agenda():
    if not dados.get("agenda_url"):
        _mark_data_ok_locked("agenda")
        return
    before = _snapshot_value(dados.get("agenda", []))
    _run_provider("agenda", lambda: agenda_provider.fetch_agenda(dados, http_client, Calendar, ICAL_AVAILABLE, logger))
    if dados.get("agenda") != before:
        _mark_data_ok_locked("agenda")


@state_write
def fetch_stocks():
    _run_provider("stocks", lambda: stocks_provider.fetch_stocks(dados, http_client))
    st = dados.get("stocks", {})
    if dados["status"].get("stocks") and any(abs(float(st.get(k, 0))) > 0 for k in ("ibov", "sp500", "nasdaq")):
        _mark_data_ok_locked("stocks")


@state_write
def fetch_printer_data():
    _run_provider("printer", lambda: printer_provider.fetch(dados, http_client, add_notification, cfg, logger))
    if dados["status"].get("printer"):
        _mark_data_ok_locked("printer")


def loop_atualizacao(matrix):
    global _collector_started_at, _collector_last_tick
    logger.info("op=loop_atualizacao status=started")

    if _collector_started_at <= 0:
        _collector_started_at = time.time()
    _collector_last_tick = time.time()

    _load_cached_snapshot()

    carregar_config()
    fetch_btc_only()
    fetch_extras()
    # Carrega secundarias cedo para o Dashboard nao iniciar vazio.
    fetch_secondary_coins()

    threading.Thread(
        target=lambda: (
            ler_temperatura(),
            fetch_stocks(),
            fetch_printer_data(),
            fetch_agenda(),
            save_debug_info(),
        )
    ).start()

    _persist_snapshot_if_needed(force=True)

    timer_secundarias = 0
    timer_lento = 0

    while True:
        time.sleep(2)
        _collector_last_tick = time.time()

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
            fetch_agenda()
            timer_lento = 0

        _persist_snapshot_if_needed(force=False)


def iniciar_thread(matrix):
    global _collector_thread
    t = threading.Thread(target=loop_atualizacao, args=(matrix,))
    t.daemon = True
    t.start()
    _collector_thread = t


def get_runtime_status():
    snapshot = get_state_snapshot()
    collector_alive = bool(_collector_thread and _collector_thread.is_alive())
    snapshot_ready = isinstance(snapshot, dict) and bool(snapshot) and "bitcoin" in snapshot and "status" in snapshot

    tick_age_s = None
    if _collector_last_tick > 0:
        tick_age_s = round(max(0.0, time.time() - _collector_last_tick), 3)

    collector_recent = tick_age_s is not None and tick_age_s <= 20.0
    ready = collector_alive and snapshot_ready and collector_recent

    return {
        "ready": ready,
        "collector_alive": collector_alive,
        "snapshot_ready": snapshot_ready,
        "tick_age_s": tick_age_s,
        "collector_started": _collector_started_at > 0,
    }


def get_observability_metrics():
    snapshot = get_state_snapshot()
    freshness = snapshot.get("freshness", {}) if isinstance(snapshot, dict) else {}

    providers = {}
    for name, stats in _provider_stats.items():
        providers[name] = {
            "attempts": int(stats.get("attempts", 0)),
            "success": int(stats.get("success", 0)),
            "errors": int(stats.get("errors", 0)),
            "last_ok": stats.get("last_ok"),
            "last_error": stats.get("last_error", ""),
            "last_duration_ms": int(stats.get("last_duration_ms", 0)),
        }

    return {
        "runtime": get_runtime_status(),
        "freshness": {
            "has_stale": bool(freshness.get("has_stale", False)),
            "stale": freshness.get("stale", {}),
            "age_s": freshness.get("age_s", {}),
            "ttl_s": freshness.get("ttl_s", {}),
            "offline_since": freshness.get("offline_since"),
        },
        "providers": providers,
    }




