import datetime
import math
import time
import random
from rgbmatrix import graphics

class NeonLabyrinthPage:
    def __init__(self):
        # --- PALETA DE CORES DEFINITIVA ---
        self.C_BG = (0, 0, 0)
        self.C_WALL = graphics.Color(0, 50, 180)        # Azul escuro clássico
        self.C_CYAN = graphics.Color(0, 255, 255)       # Ciano Neon
        self.C_CLOCK = graphics.Color(255, 184, 0)      # Âmbar Brilhante
        self.C_CLOCK_SH = graphics.Color(80, 0, 0)      # Sombra do relógio
        self.C_PELLET = (255, 180, 150)                 # Pontos
        self.C_HERO = (255, 224, 0)                     # Amarelo Clássico

        self.C_GHOSTS = [
            (248, 31, 248),  # Rosa
            (0, 255, 136),   # Verde
            (187, 0, 255),   # Roxo
            (255, 102, 0),   # Laranja
        ]

        # --- NÚMEROS PIXEL-ART ARCADE (5x7) ---
        self.DIGITS = [
            [0,1,1,1,0, 1,0,0,0,1, 1,0,0,0,1, 1,0,0,0,1, 1,0,0,0,1, 1,0,0,0,1, 0,1,1,1,0], # 0
            [0,0,1,0,0, 0,1,1,0,0, 0,0,1,0,0, 0,0,1,0,0, 0,0,1,0,0, 0,0,1,0,0, 0,1,1,1,0], # 1
            [0,1,1,1,0, 1,0,0,0,1, 0,0,0,0,1, 0,0,1,1,0, 0,1,0,0,0, 1,0,0,0,0, 1,1,1,1,1], # 2
            [0,1,1,1,0, 1,0,0,0,1, 0,0,0,0,1, 0,0,1,1,0, 0,0,0,0,1, 1,0,0,0,1, 0,1,1,1,0], # 3
            [1,0,0,1,0, 1,0,0,1,0, 1,0,0,1,0, 1,1,1,1,1, 0,0,0,1,0, 0,0,0,1,0, 0,0,0,1,0], # 4
            [1,1,1,1,1, 1,0,0,0,0, 1,1,1,1,0, 0,0,0,0,1, 0,0,0,0,1, 1,0,0,0,1, 0,1,1,1,0], # 5
            [0,1,1,1,0, 1,0,0,0,0, 1,1,1,1,0, 1,0,0,0,1, 1,0,0,0,1, 1,0,0,0,1, 0,1,1,1,0], # 6
            [1,1,1,1,1, 0,0,0,0,1, 0,0,0,1,0, 0,0,1,0,0, 0,1,0,0,0, 0,1,0,0,0, 0,1,0,0,0], # 7
            [0,1,1,1,0, 1,0,0,0,1, 1,0,0,0,1, 0,1,1,1,0, 1,0,0,0,1, 1,0,0,0,1, 0,1,1,1,0], # 8
            [0,1,1,1,0, 1,0,0,0,1, 1,0,0,0,1, 0,1,1,1,1, 0,0,0,0,1, 1,0,0,0,1, 0,1,1,1,0], # 9
        ]

        # --- PLANTA MESTRA DO TAUSER ---
        self.MAZE_MAP = [
            "################", # 0
            "#..............#", # 1 (Cantos Pílulas de Poder)
            "#.####.##.####.#", # 2
            "#.#..........#.#", # 3
            "#.##.######.##.#", # 4
            "#..............#", # 5
            "###.VVVVVVVV...#", # 6
            "....VVVVVVVV.###", # 7 (Saída ESQUERDA | Obstáculo Direita)
            "###.VVVVVVVV...#", # 8
            "#..............#", # 9
            "#.##.######.##.#", # 10
            "#.#..........#.#", # 11
            "#.####.##.####.#", # 12
            "#.#....##....#.#", # 13 (T Físico)
            "#..............#", # 14 (Cantos Pílulas de Poder)
            "################"  # 15
        ]

        self.nodes = {}
        self.pellets = []
        self._build_graph()

        self.entities = []
        self._reset_positions()

        self.respawn_queue = []
        self.respawn_timer = 0
        self.frightened_timer = 0

        self.breath_tick = 0.0
        self.logic_step_s = 0.033
        self._last_logic_ts = time.monotonic()
        self._logic_accum = 0.0
        self.active = False

    def _get_node_id(self, r, c):
        return r * 16 + c

    def _reset_positions(self):
        self.hero = {"type": "hero", "x": 7*4, "y": 14*4, "target": self._get_node_id(14, 7), "prev": self._get_node_id(14, 7), "dir": 1, "speed": 2, "timer": 0, "color": self.C_HERO}
        self.ghosts = [
            {"type": "ghost", "idx": 0, "x": 1*4,  "y": 1*4,  "target": self._get_node_id(1, 1),   "prev": self._get_node_id(1, 1),   "dir": 1, "speed": 3, "timer": 0, "color": self.C_GHOSTS[0]},
            {"type": "ghost", "idx": 1, "x": 14*4, "y": 1*4,  "target": self._get_node_id(1, 14),  "prev": self._get_node_id(1, 14),  "dir": 2, "speed": 3, "timer": 0, "color": self.C_GHOSTS[1]},
            {"type": "ghost", "idx": 2, "x": 1*4,  "y": 14*4, "target": self._get_node_id(14, 1),  "prev": self._get_node_id(14, 1),  "dir": 0, "speed": 3, "timer": 0, "color": self.C_GHOSTS[2]},
            {"type": "ghost", "idx": 3, "x": 14*4, "y": 14*4, "target": self._get_node_id(14, 14), "prev": self._get_node_id(14, 14), "dir": 3, "speed": 3, "timer": 0, "color": self.C_GHOSTS[3]},
        ]
        self.entities = [self.hero] + self.ghosts
        self.frightened_timer = 0

    def set_active(self, active):
        self.active = bool(active)
        if self.active:
            self._last_logic_ts = time.monotonic()
            self._logic_accum = 0.0

    def _build_graph(self):
        for r in range(16):
            for c in range(16):
                if self.MAZE_MAP[r][c] == '.':
                    node_id = self._get_node_id(r, c)
                    self.nodes[node_id] = {
                        "r": r, "c": c, "x": c * 4, "y": r * 4,
                        "neighbors": [-1, -1, -1, -1]
                    }

                    is_power = (r == 1 and c == 1) or (r == 1 and c == 14) or (r == 14 and c == 1) or (r == 14 and c == 14)

                    self.pellets.append({'id': node_id, 'x': c*4 + 1, 'y': r*4 + 1, 'active': True, 'power': is_power})

        for node_id, node in self.nodes.items():
            r, c = node["r"], node["c"]
            if self._get_node_id(r-1, c) in self.nodes: node["neighbors"][0] = self._get_node_id(r-1, c)
            if self._get_node_id(r+1, c) in self.nodes: node["neighbors"][2] = self._get_node_id(r+1, c)
            if self._get_node_id(r, c+1) in self.nodes: node["neighbors"][1] = self._get_node_id(r, c+1)
            if self._get_node_id(r, c-1) in self.nodes: node["neighbors"][3] = self._get_node_id(r, c-1)

    def fill_rect(self, canvas, x, y, w, h, color):
        for i in range(h):
            graphics.DrawLine(canvas, x, y + i, x + w - 1, y + i, color)

    def _dist(self, x1, y1, x2, y2):
        return abs(x1 - x2) + abs(y1 - y2)

    def _opposite_dir(self, direction):
        return (direction + 2) % 4

    def _node_for_entity(self, ent):
        if ent["x"] % 4 != 0 or ent["y"] % 4 != 0:
            return None
        node_id = self._get_node_id(ent["y"] // 4, ent["x"] // 4)
        return node_id if node_id in self.nodes else None

    def _moves_from_node(self, ent, current_node):
        moves = []
        for direction, neighbor in enumerate(current_node["neighbors"]):
            if neighbor != -1 and neighbor in self.nodes:
                moves.append((direction, neighbor))

        if not moves:
            return []

        no_reverse = [m for m in moves if m[0] != self._opposite_dir(ent["dir"])]
        return no_reverse if no_reverse else moves

    def _move_towards_target(self, ent):
        target_node = self.nodes.get(ent["target"])
        if not target_node:
            return

        tx, ty = target_node["x"], target_node["y"]

        if ent["x"] < tx:
            ent["x"] += 1
            ent["dir"] = 1
        elif ent["x"] > tx:
            ent["x"] -= 1
            ent["dir"] = 3
        elif ent["y"] < ty:
            ent["y"] += 1
            ent["dir"] = 2
        elif ent["y"] > ty:
            ent["y"] -= 1
            ent["dir"] = 0

        ent["x"] = max(0, min(63, ent["x"]))
        ent["y"] = max(0, min(63, ent["y"]))

    def _hero_consume_pellets(self):
        consumed_power = False
        hx, hy = self.hero["x"], self.hero["y"]

        for p in self.pellets:
            if p['active'] and self._dist(hx, hy, p["x"]-1, p["y"]-1) < 3:
                p['active'] = False
                if p.get('power'):
                    consumed_power = True

        if consumed_power:
            self.frightened_timer = 250
            for g in self.ghosts:
                if g["target"] in self.nodes and g["prev"] in self.nodes:
                    g["target"], g["prev"] = g["prev"], g["target"]
                g["dir"] = self._opposite_dir(g["dir"])

    def _choose_next_target(self, ent, current_node):
        valid_moves = self._moves_from_node(ent, current_node)
        if not valid_moves:
            return

        hx, hy = self.hero["x"], self.hero["y"]

        if ent["type"] == "hero":
            if self.frightened_timer > 0:
                alvo = min(self.ghosts, key=lambda g: self._dist(g["x"], g["y"], ent["x"], ent["y"]))
                escolha = min(valid_moves, key=lambda move: self._dist(self.nodes[move[1]]["x"], self.nodes[move[1]]["y"], alvo["x"], alvo["y"]))
                ent["dir"], ent["target"] = escolha
                return

            perigo = min(self.ghosts, key=lambda g: self._dist(g["x"], g["y"], ent["x"], ent["y"]))
            perigo_dist = self._dist(perigo["x"], perigo["y"], ent["x"], ent["y"])

            active_pellets = [p for p in self.pellets if p['active']]
            pellet_target = min(active_pellets, key=lambda p: self._dist(ent["x"], ent["y"], p["x"], p["y"])) if active_pellets else None

            if perigo_dist < 16:
                escolha = max(valid_moves, key=lambda move: self._dist(self.nodes[move[1]]["x"], self.nodes[move[1]]["y"], perigo["x"], perigo["y"]))
                ent["dir"], ent["target"] = escolha
            elif pellet_target:
                escolha = min(
                    valid_moves,
                    key=lambda move: self._dist(self.nodes[move[1]]["x"], self.nodes[move[1]]["y"], pellet_target["x"], pellet_target["y"]) + random.randint(0, 2)
                )
                ent["dir"], ent["target"] = escolha
            else:
                ent["dir"], ent["target"] = random.choice(valid_moves)
            return

        if self.frightened_timer > 0:
            escolha = max(valid_moves, key=lambda move: self._dist(self.nodes[move[1]]["x"], self.nodes[move[1]]["y"], hx, hy))
            ent["dir"], ent["target"] = escolha
            return

        alvo_x, alvo_y = hx, hy
        if ent["idx"] == 1:
            # Ambush: mira um pouco à frente do herói
            alvo_y -= 8 if self.hero["dir"] == 0 else 0
            alvo_x += 8 if self.hero["dir"] == 1 else 0
            alvo_y += 8 if self.hero["dir"] == 2 else 0
            alvo_x -= 8 if self.hero["dir"] == 3 else 0
        elif ent["idx"] == 2:
            # Patrol errático
            if random.random() < 0.35:
                ent["dir"], ent["target"] = random.choice(valid_moves)
                return
        elif ent["idx"] == 3:
            # Timid: foge se muito perto
            if self._dist(ent["x"], ent["y"], hx, hy) < 18:
                alvo_x, alvo_y = 60, 60

        escolha = min(
            valid_moves,
            key=lambda move: self._dist(self.nodes[move[1]]["x"], self.nodes[move[1]]["y"], alvo_x, alvo_y) + random.randint(0, 1)
        )
        ent["dir"], ent["target"] = escolha

    def _update_logic(self):
        if self.frightened_timer > 0:
            self.frightened_timer -= 1

        if not any(p['active'] for p in self.pellets) and not self.respawn_queue:
            self.respawn_queue = [p for p in self.pellets]
            random.shuffle(self.respawn_queue)

        if self.respawn_queue:
            self.respawn_timer += 1
            if self.respawn_timer > 5:
                p = self.respawn_queue.pop()
                p['active'] = True
                self.respawn_timer = 0

        for ent in self.entities:
            ent["timer"] += 1

            current_speed = ent["speed"]
            if ent["type"] == "ghost" and self.frightened_timer > 0:
                current_speed = 4

            if ent["timer"] < current_speed:
                continue
            ent["timer"] = 0

            current_node_id = self._node_for_entity(ent)

            if current_node_id is not None:
                if ent["target"] not in self.nodes or ent["target"] == current_node_id:
                    ent["prev"] = current_node_id
                    self._choose_next_target(ent, self.nodes[current_node_id])
            elif ent["target"] not in self.nodes:
                # Recuperação defensiva para não sair do grafo
                nearest_node_id = self._get_node_id(round(ent["y"] / 4), round(ent["x"] / 4))
                if nearest_node_id in self.nodes:
                    ent["target"] = nearest_node_id
                    ent["prev"] = nearest_node_id

            self._move_towards_target(ent)

            if ent["type"] == "hero":
                self._hero_consume_pellets()

        # --- SISTEMA DE COLISÃO ---
        for g in self.ghosts:
            dist = self._dist(g["x"], g["y"], self.hero["x"], self.hero["y"])
            if dist >= 3:
                continue

            if self.frightened_timer > 0:
                spawns = [(1,1), (1,14), (14,1), (14,14)]
                sr, sc = spawns[g["idx"]]
                g["x"], g["y"] = sc * 4, sr * 4
                g["target"] = self._get_node_id(sr, sc)
                g["prev"] = self._get_node_id(sr, sc)
                valid_moves = [i for i, n in enumerate(self.nodes[g["target"]]["neighbors"]) if n != -1]
                g["dir"] = random.choice(valid_moves) if valid_moves else 0
            else:
                # Evita sobreposição persistente em modo normal
                self._reset_positions()
                break

    def _set_px(self, canvas, x, y, color):
        if 0 <= x < 64 and 0 <= y < 64:
            canvas.SetPixel(x, y, color[0], color[1], color[2])

    def _draw_entity(self, canvas, ent):
        cx, cy = ent["x"] - 1, ent["y"] - 1

        is_frightened = (ent["type"] == "ghost" and self.frightened_timer > 0)
        blink_white = (is_frightened and self.frightened_timer < 60 and (self.frightened_timer // 5) % 2 == 0)

        if is_frightened:
            r, g, b = (255, 255, 255) if blink_white else (0, 0, 255)
        else:
            r, g, b = ent["color"]

        for i in range(5):
            for j in range(5):
                is_corner = (i==0 and j==0) or (i==4 and j==0) or (i==0 and j==4) or (i==4 and j==4)

                if ent["type"] == "hero":
                    if is_corner: continue
                    if (ent["x"] + ent["y"]) % 8 < 4:
                        if ent["dir"] == 1:
                            if i == 2 and j == 2: continue
                            if i >= 3 and 1 <= j <= 3: continue
                        elif ent["dir"] == 3:
                            if i == 2 and j == 2: continue
                            if i <= 1 and 1 <= j <= 3: continue
                        elif ent["dir"] == 0:
                            if i == 2 and j == 2: continue
                            if j <= 1 and 1 <= i <= 3: continue
                        elif ent["dir"] == 2:
                            if i == 2 and j == 2: continue
                            if j >= 3 and 1 <= i <= 3: continue
                    self._set_px(canvas, cx + i, cy + j, (r, g, b))

                else:
                    if j == 0 and (i == 0 or i == 4): continue
                    if j == 4 and (ent["x"] + ent["y"]) % 4 < 2 and (i == 1 or i == 3): continue
                    self._set_px(canvas, cx + i, cy + j, (r, g, b))

        if ent["type"] == "ghost":
            if is_frightened:
                eye_color = (255, 0, 0) if blink_white else (255, 180, 150)
                self._set_px(canvas, cx + 1, cy + 1, eye_color)
                self._set_px(canvas, cx + 3, cy + 1, eye_color)
                self._set_px(canvas, cx + 1, cy + 3, eye_color)
                self._set_px(canvas, cx + 2, cy + 2, eye_color)
                self._set_px(canvas, cx + 3, cy + 3, eye_color)
            else:
                self._set_px(canvas, cx + 1, cy + 1, (255, 255, 255))
                self._set_px(canvas, cx + 3, cy + 1, (255, 255, 255))

                px1, py1 = cx + 1, cy + 1
                px2, py2 = cx + 3, cy + 1

                if ent["dir"] == 1: px1 += 1; px2 += 1
                elif ent["dir"] == 3: px1 -= 1; px2 -= 1
                elif ent["dir"] == 0: py1 -= 1; py2 -= 1
                elif ent["dir"] == 2: py1 += 1; py2 += 1

                self._set_px(canvas, px1, py1, (0, 0, 255))
                self._set_px(canvas, px2, py2, (0, 0, 255))

    def _draw_maze_walls(self, canvas):
        C_BASE = self.C_WALL
        C_EXIT = self.C_CYAN

        for r in range(16):
            for c in range(16):
                if self.MAZE_MAP[r][c] == '#':
                    bx, by = c * 4, r * 4
                    color = C_BASE

                    if (r == 6 or r == 8) and c < 2:
                        color = C_EXIT

                    self.fill_rect(canvas, bx + 1, by + 1, 2, 2, color)

                    if c < 15 and self.MAZE_MAP[r][c+1] == '#':
                        next_color = C_EXIT if (r == 6 or r == 8) and (c + 1) < 2 else C_BASE
                        self.fill_rect(canvas, bx + 3, by + 1, 2, 2, next_color)

                    if r < 15 and self.MAZE_MAP[r+1][c] == '#':
                        self.fill_rect(canvas, bx + 1, by + 3, 2, 2, color)

    def _draw_digit(self, canvas, start_x, start_y, val, color):
        for row in range(7):
            for col in range(5):
                if self.DIGITS[val][row*5 + col]:
                    self.fill_rect(canvas, start_x + col, start_y + row, 1, 1, color)

    def _draw_clock(self, canvas):
        now = datetime.datetime.now()
        h_str = f"{now.hour:02d}"
        m_str = f"{now.minute:02d}"

        y_pos = 26
        x = 18

        self._draw_digit(canvas, x+1, y_pos+1, int(h_str[0]), self.C_CLOCK_SH)
        self._draw_digit(canvas, x+7, y_pos+1, int(h_str[1]), self.C_CLOCK_SH)
        self._draw_digit(canvas, x+17, y_pos+1, int(m_str[0]), self.C_CLOCK_SH)
        self._draw_digit(canvas, x+23, y_pos+1, int(m_str[1]), self.C_CLOCK_SH)

        self._draw_digit(canvas, x, y_pos, int(h_str[0]), self.C_CLOCK)
        self._draw_digit(canvas, x+6, y_pos, int(h_str[1]), self.C_CLOCK)
        self._draw_digit(canvas, x+16, y_pos, int(m_str[0]), self.C_CLOCK)
        self._draw_digit(canvas, x+22, y_pos, int(m_str[1]), self.C_CLOCK)

        self.breath_tick += 0.1
        if math.sin(self.breath_tick) > 0:
            self.fill_rect(canvas, x+13, y_pos+2, 2, 2, self.C_CLOCK_SH)
            self.fill_rect(canvas, x+13, y_pos+5, 2, 2, self.C_CLOCK_SH)
            self.fill_rect(canvas, x+12, y_pos+1, 2, 2, self.C_CLOCK)
            self.fill_rect(canvas, x+12, y_pos+4, 2, 2, self.C_CLOCK)

    def draw_frame(self, canvas):
        now = time.monotonic()
        if self.active:
            elapsed = min(0.2, max(0.0, now - self._last_logic_ts))
            self._last_logic_ts = now
            self._logic_accum += elapsed

            ticks = 0
            while self._logic_accum >= self.logic_step_s and ticks < 5:
                self._update_logic()
                self._logic_accum -= self.logic_step_s
                ticks += 1
        else:
            self._last_logic_ts = now
            self._logic_accum = 0.0

        canvas.Clear()

        self._draw_maze_walls(canvas)

        for p in self.pellets:
            if p['active']:
                if p.get('power'):
                    if math.sin(self.breath_tick * 2) > 0:
                        c_power = graphics.Color(self.C_PELLET[0], self.C_PELLET[1], self.C_PELLET[2])
                        self.fill_rect(canvas, p["x"]-1, p["y"]-1, 3, 3, c_power)
                else:
                    self._set_px(canvas, p["x"], p["y"], self.C_PELLET)

        for ent in self.entities:
            self._draw_entity(canvas, ent)

        C_BASE = self.C_WALL
        graphics.DrawLine(canvas, 0, 0, 63, 0, C_BASE)
        graphics.DrawLine(canvas, 0, 63, 63, 63, C_BASE)

        graphics.DrawLine(canvas, 0, 0, 0, 27, C_BASE)
        graphics.DrawLine(canvas, 0, 32, 0, 63, C_BASE)

        graphics.DrawLine(canvas, 63, 0, 63, 63, C_BASE)

        self._draw_clock(canvas)

_page = NeonLabyrinthPage()

def on_activate():
    _page.set_active(True)

def on_deactivate():
    _page.set_active(False)

def draw(canv):
    _page.draw_frame(canv)



