import os
from rgbmatrix import RGBMatrixOptions, graphics

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- CONFIGURAÇÕES DE TEMPO ---
FADE_SPEED = 4

# --- PLAYLIST ---
PLAYLIST = [
    {"id": "DASHBOARD", "tempo": 30},
    {"id": "BOLSA",     "tempo": 15},
    {"id": "GALERIA",   "tempo": 10}
]

# --- HARDWARE ---
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat-pwm'
options.gpio_slowdown = 4
options.drop_privileges = False
options.disable_hardware_pulsing = False
options.pwm_lsb_nanoseconds = 130
options.limit_refresh_rate_hz = 60

# --- ROTAÇÃO DA TELA ---
# Descomente a linha abaixo para rotacionar. Valores: "Rotate:90", "Rotate:180", "Rotate:270"
options.pixel_mapper_config = "Rotate:180"

# --- FONTES (Carregamento Seguro) ---
try:
    font_s = graphics.Font()
    font_s.LoadFont(os.path.join(BASE_DIR, "fonts/4x6.bdf"))
    
    font_m = graphics.Font()
    font_m.LoadFont(os.path.join(BASE_DIR, "fonts/5x8.bdf"))
    
    font_l = graphics.Font()
    font_l.LoadFont(os.path.join(BASE_DIR, "fonts/6x10.bdf"))
except Exception as e:
    print(f"Erro ao carregar fontes: {e}. Usando padrão.")
    font_s = graphics.Font()
    font_s.LoadFont(os.path.join(BASE_DIR, "fonts/6x10.bdf"))
    font_m = font_s
    font_l = font_s

# Tenta carregar a fonte Tiny separadamente. Se falhar, usa a Small (4x6)
try:
    font_t = graphics.Font()
    font_t.LoadFont(os.path.join(BASE_DIR, "fonts/tom-thumb.bdf"))
except:
    font_t = font_s

# --- CORES (AQUI ESTAVA O ERRO - AGORA SÃO OBJETOS) ---
C_WHITE     = graphics.Color(255, 255, 255)
C_GOLD      = graphics.Color(255, 215, 0)
C_RED       = graphics.Color(255, 0, 0)
C_GREEN     = graphics.Color(0, 255, 0)
C_BLUE      = graphics.Color(0, 0, 255)
C_ORANGE    = graphics.Color(255, 165, 0)
C_YELLOW    = graphics.Color(255, 255, 0)
C_TEAL      = graphics.Color(0, 128, 128)
C_GREY      = graphics.Color(50, 50, 50)
C_DIM       = graphics.Color(100, 100, 100)
C_BG_HEADER = graphics.Color(0, 0, 50)  # <-- O erro do log era aqui!

# Cores da Matrix Rain
C_MAT_HEAD  = graphics.Color(200, 255, 200)
C_MAT_TAIL  = graphics.Color(0, 100, 0)

# --- GIFS ---
ANIMACAO_FILE = os.path.join(BASE_DIR, "images/memecoin.gif")
ANIMACAO_W = 29
ANIMACAO_H = 19

GIF_SPEED = 0.1
TEMPO_SLIDE = 5