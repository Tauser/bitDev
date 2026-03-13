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
import utils
from infra.logging_config import get_logger
from pages import dashboard, bolsa, galeria, impressora, clima, relogio, agenda

watchdog_stop_event = threading.Event()
logger = get_logger(__name__)


def sd_notify(msg):
    sock = os.environ.get("NOTIFY_SOCKET")
    if not sock:
        return
    try:
        if sock.startswith("@"):
            sock = "\0" + sock[1:]
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
            s.connect(sock)
            s.sendall(msg.encode())
    except OSError:
        pass


def watchdog_heartbeat(interval_s=5):
    while not watchdog_stop_event.wait(interval_s):
        sd_notify("WATCHDOG=1")


def iniciar_web():
    try:
        web_app.app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    except Exception as exc:
        logger.exception("op=iniciar_web status=failed reason=%s", exc)


logger.info("op=boot stage=web_start")
threading.Thread(target=iniciar_web, daemon=True).start()
threading.Thread(target=watchdog_heartbeat, daemon=True).start()

logger.info("op=boot stage=hardware_init")
matrix = RGBMatrix(options=cfg.options)
canvas = matrix.CreateFrameCanvas()

data.iniciar_thread(matrix)

indice_playlist = 0
ultimo_checkpoint = time.time()
pagina_ativa_id = None

PAGE_MODULES = {
    "DASHBOARD": dashboard,
    "BOLSA": bolsa,
    "GALERIA": galeria,
    "IMPRESSORA": impressora,
    "CLIMA": clima,
    "RELOGIO": relogio,
    "AGENDA": agenda,
}


def _notify_page_lifecycle(page_id, active):
    module = PAGE_MODULES.get(page_id)
    if module is None:
        return

    fn_name = "on_activate" if active else "on_deactivate"
    fn = getattr(module, fn_name, None)
    if callable(fn):
        try:
            fn()
        except Exception as exc:
            logger.warning("op=page_lifecycle status=failed page=%s hook=%s reason=%s", page_id, fn_name, exc)


def _set_pagina_ativa(page_id):
    global pagina_ativa_id

    if pagina_ativa_id == page_id:
        return

    if pagina_ativa_id is not None:
        _notify_page_lifecycle(pagina_ativa_id, False)

    pagina_ativa_id = page_id
    _notify_page_lifecycle(pagina_ativa_id, True)


def obter_playlist_ativa():
    try:
        path = os.path.join(cfg.BASE_DIR, "user_config.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                d = json.load(f)

            paginas = []
            now = time.localtime()
            curr_min = now.tm_hour * 60 + now.tm_min

            for p in d.get("pages", []):
                if not p.get("enabled", True):
                    continue

                inicio = p.get("inicio", "00:00")
                fim = p.get("fim", "23:59")

                try:
                    ih, im = map(int, inicio.split(":"))
                    fh, fm = map(int, fim.split(":"))
                    start = ih * 60 + im
                    end = fh * 60 + fm

                    if start <= end:
                        if not (start <= curr_min <= end):
                            continue
                    else:
                        if not (curr_min >= start or curr_min <= end):
                            continue
                except (TypeError, ValueError):
                    pass

                paginas.append(p)

            if not paginas:
                return [{"id": "DASHBOARD", "tempo": 10}]
            return paginas
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("op=playlist_load status=failed reason=%s", exc)

    return cfg.PLAYLIST


def get_tempo_segundos(tela_conf):
    try:
        tempo = int(tela_conf.get("tempo", 10))
    except (TypeError, ValueError, AttributeError):
        tempo = 10
    return max(1, min(120, tempo))


def desenhar_tela_generica(canv, tela_conf):
    if tela_conf["id"] == "GALERIA":
        galeria.draw(canv)
    else:
        titulo = None
        if tela_conf["id"] == "BOLSA":
            titulo = "MERCADO"
        elif tela_conf["id"] == "AGENDA":
            titulo = "AGENDA"

        header_col = cfg.C_TEAL
        if tela_conf["id"] == "DASHBOARD":
            header_col = cfg.C_ORANGE
        elif tela_conf["id"] == "BOLSA":
            header_col = cfg.C_BLUE
        elif tela_conf["id"] == "AGENDA":
            header_col = cfg.C_GOLD

        if tela_conf["id"] not in ["IMPRESSORA", "CLIMA", "RELOGIO"]:
            layout.draw_header(canv, titulo, header_col)

        if tela_conf["id"] == "DASHBOARD":
            dashboard.draw(canv)
        elif tela_conf["id"] == "BOLSA":
            bolsa.draw(canv)
        elif tela_conf["id"] == "IMPRESSORA":
            impressora.draw(canv)
        elif tela_conf["id"] == "CLIMA":
            clima.draw(canv)
        elif tela_conf["id"] == "RELOGIO":
            relogio.draw(canv)
        elif tela_conf["id"] == "AGENDA":
            agenda.draw(canv)

        if tela_conf["id"] not in ["IMPRESSORA", "CLIMA", "RELOGIO", "AGENDA"]:
            layout.draw_footer(canv)


playlist_atual = obter_playlist_ativa()


def realizar_transicao_fade():
    global indice_playlist, ultimo_checkpoint, playlist_atual, canvas

    nova_playlist = obter_playlist_ativa()
    if not nova_playlist:
        nova_playlist = [{"id": "DASHBOARD", "tempo": 10}]

    animations.fade_transition(matrix, 0, cfg.FADE_SPEED)

    canvas.Clear()
    canvas = matrix.SwapOnVSync(canvas)

    playlist_atual = nova_playlist

    if indice_playlist >= len(playlist_atual):
        indice_playlist = 0

    snap = data.get_state_snapshot()
    status = snap.get("status", {}) if isinstance(snap, dict) else {}

    proximo_idx = indice_playlist
    proxima_tela = None

    for i in range(1, len(playlist_atual) + 1):
        idx = (indice_playlist + i) % len(playlist_atual)
        cand = playlist_atual[idx]
        pid = cand["id"]

        if pid == "IMPRESSORA" and not status.get("printer", False):
            continue
        if pid == "BOLSA" and not status.get("stocks", False):
            continue
        if pid == "GALERIA" and not galeria.tem_imagens():
            continue

        proximo_idx = idx
        proxima_tela = cand
        break

    if proxima_tela is None:
        proximo_idx = 0
        proxima_tela = playlist_atual[0]

    indice_playlist = proximo_idx

    _set_pagina_ativa(proxima_tela["id"])

    if proxima_tela["id"] == "GALERIA":
        galeria.sortear_novo()
    elif proxima_tela["id"] == "DASHBOARD":
        dashboard.init()

    canvas.Clear()
    desenhar_tela_generica(canvas, proxima_tela)
    canvas = matrix.SwapOnVSync(canvas)
    ultimo_checkpoint = time.time()

    brilho_alvo = snap.get("brilho", 70) if isinstance(snap, dict) else 70
    if isinstance(snap, dict) and snap.get("modo_noturno", False):
        h = time.localtime().tm_hour
        if h >= 22 or h < 6:
            brilho_alvo = min(brilho_alvo, 30)

    animations.fade_transition(matrix, brilho_alvo, cfg.FADE_SPEED)


logger.info("op=boot stage=main_loop")
animations.executar_matrix_rain(canvas, matrix)

if playlist_atual[indice_playlist]["id"] == "DASHBOARD":
    dashboard.init()

_set_pagina_ativa(playlist_atual[indice_playlist]["id"])

ultimo_checkpoint = time.time()
sd_notify("READY=1")

try:
    while True:
        try:
            agora = time.time()
            tela_config = playlist_atual[indice_playlist]
            tempo_tela = get_tempo_segundos(tela_config)

            if agora - ultimo_checkpoint > tempo_tela:
                realizar_transicao_fade()
                agora = time.time()
                tela_config = playlist_atual[indice_playlist]

            canvas.Clear()

            snap = data.get_state_snapshot()
            brilho_atual = snap.get("brilho", 70) if isinstance(snap, dict) else 70

            if isinstance(snap, dict) and snap.get("modo_noturno", False):
                h = time.localtime().tm_hour
                if h >= 22 or h < 6:
                    brilho_atual = min(brilho_atual, 30)

            if matrix.brightness != brilho_atual:
                matrix.brightness = brilho_atual

            if isinstance(snap, dict) and not snap.get("conexao", True) and tela_config["id"] in ["DASHBOARD", "BOLSA"]:
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

            desenhar_tela_generica(canvas, tela_config)
            time.sleep(0.05)

            canvas = matrix.SwapOnVSync(canvas)

        except Exception as exc:
            logger.exception("op=main_loop status=recoverable_error reason=%s", exc)
            time.sleep(1)
            continue

except KeyboardInterrupt:
    watchdog_stop_event.set()
    sys.exit(0)

