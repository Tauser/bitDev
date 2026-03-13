import os
import random
import time
import config as cfg
import utils
import animations
import data

# --- ESTADO LOCAL ---
frames_pixelart_cheio = []
anim_art_idx = 0
ultimo_gif_nome = ""
last_frame_time = 0


def tem_imagens():
    try:
        pasta = os.path.join(cfg.BASE_DIR, "images/pixelart")
        if not os.path.exists(pasta):
            return False
        return any(f.lower().endswith('.gif') for f in os.listdir(pasta))
    except Exception:
        return False


def sortear_novo():
    """Sorteia um novo GIF da pasta"""
    global frames_pixelart_cheio, anim_art_idx, ultimo_gif_nome
    pasta = os.path.join(cfg.BASE_DIR, "images/pixelart")

    if not os.path.exists(pasta):
        try:
            os.makedirs(pasta)
        except Exception:
            pass

    gifs = [f for f in os.listdir(pasta) if f.lower().endswith('.gif')]

    if gifs:
        escolhido = random.choice(gifs)
        # Tenta não repetir o mesmo GIF seguido
        if len(gifs) > 1 and escolhido == ultimo_gif_nome:
            while escolhido == ultimo_gif_nome:
                escolhido = random.choice(gifs)

        ultimo_gif_nome = escolhido
        print(f"--> GIF Sorteado: {escolhido}")

        caminho_completo = os.path.join(pasta, escolhido)
        frames_pixelart_cheio = animations.carregar_gif(caminho_completo, 64, 64)
        anim_art_idx = 0
    else:
        frames_pixelart_cheio = []


def draw(canv):
    state = data.get_state_snapshot()
    global anim_art_idx, last_frame_time

    speed = state.get('gif_speed', 0.1)

    if frames_pixelart_cheio:
        try:
            canv.SetImage(frames_pixelart_cheio[anim_art_idx], 0, 0)
            if time.time() - last_frame_time > speed:
                anim_art_idx = (anim_art_idx + 1) % len(frames_pixelart_cheio)
                last_frame_time = time.time()
        except Exception:
            pass
    else:
        utils.draw_no_images_placeholder(canv, cfg)
