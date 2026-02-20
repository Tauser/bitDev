from rgbmatrix import graphics

def to_matrix_color(color):
    if isinstance(color, tuple):
        return graphics.Color(*color)
    return color

def draw_center(canvas, font, y, color, text, shadow=False):
    text = str(text)
    text_len = sum(font.CharacterWidth(ord(c)) for c in text)
    x = (64 - text_len) // 2
    
    if shadow:
        graphics.DrawText(canvas, font, x + 1, y + 1, graphics.Color(0, 0, 0), text)
        
    graphics.DrawText(canvas, font, x, y, to_matrix_color(color), text)

def draw_bold(canvas, font, x, y, color, text):
    c_obj = to_matrix_color(color)
    graphics.DrawText(canvas, font, x, y, c_obj, str(text))
    graphics.DrawText(canvas, font, x + 1, y, c_obj, str(text))

def draw_arrow(canvas, x, y, is_up):
    color = graphics.Color(0, 255, 0) if is_up else graphics.Color(255, 0, 0)
    
    if is_up:
        coords = [(x+2,y), (x+1,y+1), (x+3,y+1), (x,y+2), (x+4,y+2)]
    else:
        coords = [(x,y), (x+4,y), (x+1,y+1), (x+3,y+1), (x+2,y+2)]
        
    for cx, cy in coords:
        canvas.SetPixel(cx, cy, color.red, color.green, color.blue)

def draw_text_shadow(canvas, font, x, y, color, text):
    c_shadow = graphics.Color(0, 0, 0)
    graphics.DrawText(canvas, font, x + 1, y + 1, c_shadow, str(text))
    graphics.DrawText(canvas, font, x, y, to_matrix_color(color), str(text))