#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import curses
import json
import random
import time
import os
import shutil
import subprocess
import copy
import sys

game_data = {
    'board_width': 10,
    'board_height': 20,
    'preview_width': 6,
    'preview_height': 4,
    'lines_per_level': 10,
    'lock_frames': 30,
    'max_lock_resets': 15,
}

DISPLAY_CHARS = {
    'block': '██',
    'empty': '  ',
    'ghost': '▒▒',
}

KEY_NAME_MAP = {
    'LEFT':         curses.KEY_LEFT,
    'RIGHT':        curses.KEY_RIGHT,
    'UP':           curses.KEY_UP,
    'DOWN':         curses.KEY_DOWN,
    'HOME':         curses.KEY_HOME,
    'END':          curses.KEY_END,
    'PPAGE':        curses.KEY_PPAGE,
    'NPAGE':        curses.KEY_NPAGE,
    'ENTER':        10,
    'TAB':          9,
    'ESC':          27,
    'BTAB':         curses.KEY_BTAB,
    'SPACE':        ord(' '),
    'ENTER':        10,
    'TAB':          9,
    'ESC':          27,
}

DEFAULT_KEY_CONFIG_JSON = {
    'left':         ['KEY_LEFT'],
    'right':        ['KEY_RIGHT'],
    'soft_drop':    ['KEY_DOWN'],
    'rotate_cw':    ['KEY_UP', 'x'],
    'rotate_ccw':   ['z'],
    'rotate_180':   ['a'],
    'hard_drop':    ['SPACE'],
    'hold':         ['c'],
    'pause':        ['p'],
    'quit':         ['q', 'ESC'],
    'restart':      ['r'],
}

CONFIG_DIR = os.path.expanduser('~/.config/terminal-tetris')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

def parse_key_name(name):
    """转换为 curses 键码"""
    if name in KEY_NAME_MAP:
        return [KEY_NAME_MAP[name]]
    if len(name) == 1:
        code = ord(name)
        if name.isalpha():
            lower = ord(name.lower())
            upper = ord(name.upper())
            return [lower, upper]
        return [code]

    try:
        return [getattr(curses, name)]
    except AttributeError:
        pass

    if len(name) > 0:
        return [ord(name[0])]

    return [0]


class Config:
    def __init__(self):
        self.path = CONFIG_FILE
        os.makedirs(CONFIG_DIR, exist_ok=True)

    def create(self):
        """创建空配置文件"""
        if not os.path.exists(self.path):
            try:
                with open(self.path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
            except Exception:
                pass

    def write(self, key, value):
        """写入配置项"""
        self.create()
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
        data[key] = value
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def read(self, key, default=None):
        """读取配置项如果不存在时写入默认值"""
        self.create()
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
        if key not in data:
            data[key] = default
            try:
                with open(self.path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            except Exception:
                pass
        return data.get(key, default)


def load_key_config():
    """加载按键配置"""
    config = Config()
    raw = config.read('key_bindings', DEFAULT_KEY_CONFIG_JSON)

    key_config = {}
    for action, keys in raw.items():
        if not isinstance(keys, list):
            keys = [keys]
        result = []
        for k in keys:
            result.extend(parse_key_name(k))
        key_config[action] = result

    for action, default_keys in DEFAULT_KEY_CONFIG_JSON.items():
        if action not in key_config or not key_config[action]:
            result = []
            for k in default_keys:
                result.extend(parse_key_name(k))
            key_config[action] = result

    return key_config


SHAPES = {
    'I': [
        [0,0,0,0],
        [1,1,1,1],
        [0,0,0,0],
        [0,0,0,0]
    ],
    'O': [
        [1,1],
        [1,1]
    ],
    'T': [
        [0,1,0],
        [1,1,1],
        [0,0,0]
    ],
    'S': [
        [0,1,1],
        [1,1,0],
        [0,0,0]
    ],
    'Z': [
        [1,1,0],
        [0,1,1],
        [0,0,0]
    ],
    'J': [
        [1,0,0],
        [1,1,1],
        [0,0,0]
    ],
    'L': [
        [0,0,1],
        [1,1,1],
        [0,0,0]
    ]
}

SHAPE_RGB_COLORS = {
    'Z': '#FF5E62',  # 红
    'L': '#FF9F43',  # 橙
    'O': '#FEE140',  # 黄
    'S': '#26DE81',  # 绿
    'I': '#2ACBFF',  # 青
    'J': '#4B7BEC',  # 蓝
    'T': '#A55EEA',  # 紫
}

SHAPE_COLORS = {name: i + 1 for i, name in enumerate(SHAPE_RGB_COLORS)}

LINE_POINTS = {1: 100, 2: 300, 3: 500, 4: 800}

BORDER_STYLES = {
    'block': [
        '▄', '▄', '▄',
        '█',      '█',
        '▀', '▀', '▀'
    ],
    'double_line': [
        '╔', '═', '╗',
        '║',      '║',
        '╚', '═', '╝'
    ],
}

DEFAULT_STYLE = {
    'border': 'block',
}


SRS_KICKS_JLSTZ = {
    '0->R': [(0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)],
    'R->0': [(0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)],
    'R->2': [(0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)],
    '2->R': [(0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)],
    '2->L': [(0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)],
    'L->2': [(0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)],
    'L->0': [(0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)],
    '0->L': [(0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)],
}

SRS_KICKS_I = {
    '0->R': [(0, 0), (-2, 0), (+1, 0), (-2, -1), (+1, +2)],
    'R->0': [(0, 0), (+2, 0), (-1, 0), (+2, +1), (-1, -2)],
    'R->2': [(0, 0), (-1, 0), (+2, 0), (-1, +2), (+2, -1)],
    '2->R': [(0, 0), (+1, 0), (-2, 0), (+1, -2), (-2, +1)],
    '2->L': [(0, 0), (+2, 0), (-1, 0), (+2, +1), (-1, -2)],
    'L->2': [(0, 0), (-2, 0), (+1, 0), (-2, -1), (+1, +2)],
    'L->0': [(0, 0), (+1, 0), (-2, 0), (+1, -2), (-2, +1)],
    '0->L': [(0, 0), (-1, 0), (+2, 0), (-1, +2), (+2, -1)],
}

SRS_KICKS_O = {}


def hex_to_rgb(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return (r, g, b)


class Ansi:
    fg = lambda self, r, g, b: f'\x1b[38;2;{r};{g};{b}m'
    bg = lambda self, r, g, b: f'\x1b[48;2;{r};{g};{b}m'
    reset = lambda self: '\x1b[0m'
    bold = lambda self: '\x1b[1m'
    dim = lambda self: '\x1b[2m'
    reverse = lambda self: '\x1b[7m'
    cursor = lambda self, y, x: f'\x1b[{y};{x}H'
    clear_screen = lambda self: '\x1b[2J'
    hide_cursor = lambda self: '\x1b[?25l'
    show_cursor = lambda self: '\x1b[?25h'


def get_srs_kicks(shape_name, from_rot, to_rot):
    key = f"{from_rot}->{to_rot}"
    if shape_name == 'I':
        return SRS_KICKS_I.get(key, [])
    elif shape_name == 'O':
        return []
    else:
        return SRS_KICKS_JLSTZ.get(key, [])


def key_code_to_display(key_code):
    """将键码转换为可读的显示名称"""
    for name, code in KEY_NAME_MAP.items():
        if code == key_code:
            if name == 'SPACE':
                return '⌴'
            elif name == 'ESC':
                return '⎋'
            elif name == 'ENTER':
                return '↩'
            elif name == 'TAB':
                return '⇥'
            elif name == 'BTAB':
                return '⇤'
            elif name == 'KEY_LEFT':
                return '←'
            elif name == 'KEY_RIGHT':
                return '→'
            elif name == 'KEY_UP':
                return '↑'
            elif name == 'KEY_DOWN':
                return '↓'
            elif name == 'KEY_HOME':
                return 'Home'
            elif name == 'KEY_END':
                return 'End'
            elif name == 'KEY_PPAGE':
                return 'PgUp'
            elif name == 'KEY_NPAGE':
                return 'PgDn'
            return name
    if 32 <= key_code <= 126:
        return chr(key_code).upper()
    return f'0x{key_code:02x}'


class AudioPlayer:
    def __init__(self, filepath="./tetris.mp3"):
        self.filepath = os.path.expanduser(filepath)
        self.process = None

    def play(self):
        if not os.path.exists(self.filepath):
            return
        if self.process is not None:
            return
        if shutil.which("mpv") is None:
            return
        try:
            self.process = subprocess.Popen(
                ["mpv", "--no-video", "--loop-file=inf", "--really-quiet", self.filepath],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self.process = None

    def stop(self):
        if self.process is None:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=2)
        except Exception:
            try:
                self.process.kill()
                self.process.wait(timeout=1)
            except Exception:
                pass
        self.process = None


class Piece:
    def __init__(self, shape_name, x, y):
        self.shape_name = shape_name
        self.shape = [row[:] for row in SHAPES[shape_name]]
        self.color = SHAPE_COLORS[shape_name]
        self.x = x
        self.y = y
        self.rotation = 0  # 0=spawn, R=1, 2=2, L=3

    def rotate_matrix(self, shape, clockwise=True):
        if clockwise:
            return [list(row) for row in zip(*shape[::-1])]
        else:
            return [list(row) for row in zip(*shape)][::-1]

    def rotate_180(self, shape):
        return [list(row)[::-1] for row in shape[::-1]]

    def get_positions(self, shape=None, offset_x=0, offset_y=0):
        if shape is None:
            shape = self.shape
        positions = []
        for dy, row in enumerate(shape):
            for dx, cell in enumerate(row):
                if cell:
                    positions.append((self.x + dx + offset_x, self.y + dy + offset_y))
        return positions


class TetrisGame:
    def __init__(self, stdscr, audio=None, key_config=None):
        self.stdscr = stdscr
        self.audio = audio
        self.key_config = key_config
        gd = game_data
        self.board_width = gd['board_width']
        self.board_height = gd['board_height']
        self.board = [[0] * gd['board_width'] for _ in range(gd['board_height'])]
        self.board_colors = [[0] * gd['board_width'] for _ in range(gd['board_height'])]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.quit = False

        self.disp_y = 1
        self.disp_x = 2

        self.bag = []
        self.next_piece_name = None
        self.current_piece = None
        self.held_piece_name = None
        self.can_hold = True
        self._refill_bag()
        self._spawn_piece()

        self.g_accum = 0.0
        self.lock_frames = gd['lock_frames']
        self.lock_counter = None
        self.lock_resets = 0
        self.max_lock_resets = gd['max_lock_resets']

        self.stdscr.nodelay(True)

        config = Config()
        self.style = config.read('style', DEFAULT_STYLE)

    def _refill_bag(self):
        self.bag = list(SHAPES.keys())
        random.shuffle(self.bag)

    def _get_next_piece_name(self):
        if not self.bag:
            self._refill_bag()
        return self.bag.pop(0)

    def _spawn_piece(self):
        if self.next_piece_name is None:
            self.next_piece_name = self._get_next_piece_name()

        spawn_x = (self.board_width - len(SHAPES[self.next_piece_name][0])) // 2
        self.current_piece = Piece(self.next_piece_name, spawn_x, 0)
        self.next_piece_name = self._get_next_piece_name()
        self.lock_counter = None
        self.lock_resets = 0
        self.can_hold = True

        if not self._is_valid_position(self.current_piece):
            self.game_over = True

        self._update_ghost()

    def _is_valid_position(self, piece, shape=None, offset_x=0, offset_y=0):
        if shape is None:
            shape = piece.shape
        for x, y in piece.get_positions(shape, offset_x, offset_y):
            if x < 0 or x >= self.board_width or y >= self.board_height:
                return False
            if y >= 0 and self.board[y][x]:
                return False
        return True

    def _lock_piece(self):
        for x, y in self.current_piece.get_positions():
            if 0 <= y < self.board_height and 0 <= x < self.board_width:
                self.board[y][x] = 1
                self.board_colors[y][x] = self.current_piece.color
        self._clear_lines()
        self._spawn_piece()

    def _clear_lines(self):
        lines_cleared = 0
        y = self.board_height - 1
        while y >= 0:
            if all(self.board[y]):
                del self.board[y]
                del self.board_colors[y]
                self.board.insert(0, [0] * self.board_width)
                self.board_colors.insert(0, [0] * self.board_width)
                lines_cleared += 1
            else:
                y -= 1

        if lines_cleared > 0:
            self.lines += lines_cleared
            self.score += LINE_POINTS.get(lines_cleared, lines_cleared * 100) * self.level
            self.level = self.lines // game_data['lines_per_level'] + 1

    def _update_ghost(self):
        piece = self.current_piece
        if not piece:
            return
        drop = 0
        while self._is_valid_position(piece, offset_y=drop + 1):
            drop += 1
        self.ghost_y = piece.y + drop

    def _try_move(self, dx, dy):
        if self._is_valid_position(self.current_piece, offset_x=dx, offset_y=dy):
            self.current_piece.x += dx
            self.current_piece.y += dy
            self._update_ghost()
            if self.lock_counter is not None and self.lock_resets < self.max_lock_resets:
                self.lock_counter = 0
                self.lock_resets += 1
            return True
        return False

    def _try_rotate(self, clockwise=True, rotate_180=False):
        piece = self.current_piece
        old_shape = piece.shape
        old_rot = piece.rotation

        if rotate_180:
            new_shape = piece.rotate_180(old_shape)
            rot_map = {0: '2', 1: 'L', 2: '0', 3: 'R'}
        elif clockwise:
            new_shape = piece.rotate_matrix(old_shape, clockwise=True)
            rot_map = {0: 'R', 1: '2', 2: 'L', 3: '0'}
        else:
            new_shape = piece.rotate_matrix(old_shape, clockwise=False)
            rot_map = {0: 'L', 1: '0', 2: 'R', 3: '2'}

        from_rot_name = {0: '0', 1: 'R', 2: '2', 3: 'L'}[old_rot]
        to_rot_name = rot_map[old_rot]

        kicks = get_srs_kicks(piece.shape_name, from_rot_name, to_rot_name)

        if not kicks:
            if self._is_valid_position(piece, new_shape):
                piece.shape = new_shape
                piece.rotation = {'0': 0, 'R': 1, '2': 2, 'L': 3}[to_rot_name]
                self._update_ghost()
                if self.lock_counter is not None and self.lock_resets < self.max_lock_resets:
                    self.lock_counter = 0
                    self.lock_resets += 1
                return True
            return False

        for dx, dy in kicks:
            if self._is_valid_position(piece, new_shape, offset_x=dx, offset_y=-dy):
                piece.shape = new_shape
                piece.rotation = {'0': 0, 'R': 1, '2': 2, 'L': 3}[to_rot_name]
                piece.x += dx
                piece.y += -dy
                self._update_ghost()
                if self.lock_counter is not None and self.lock_resets < self.max_lock_resets:
                    self.lock_counter = 0
                    self.lock_resets += 1
                return True

        return False

    def _hard_drop(self):
        drop = 0
        while self._is_valid_position(self.current_piece, offset_y=drop + 1):
            drop += 1
        self.current_piece.y += drop
        self.score += drop * 2
        self._lock_piece()
        self.g_accum = 0.0

    def _hold_piece(self):
        if not self.can_hold:
            return False

        current_name = self.current_piece.shape_name

        if self.held_piece_name is None:
            self.held_piece_name = current_name
            self._spawn_piece()
        else:
            self.held_piece_name, temp = current_name, self.held_piece_name
            spawn_x = (self.board_width - len(SHAPES[temp][0])) // 2
            self.current_piece = Piece(temp, spawn_x, 0)
            self.lock_counter = None
            self.lock_resets = 0
            if not self._is_valid_position(self.current_piece):
                self.game_over = True
            self._update_ghost()

        self.can_hold = False
        return True

    def _get_gravity(self):
        if self.level >= 19:
            return 20.00

        i = self.level - 1
        time_per_cell = (0.8 - (i * 0.007)) ** i
        return 1.0 / (60.0 * time_per_cell)

    def _screen_pos(self, board_y, board_x):
        return (self.disp_y + 1 + board_y, self.disp_x + 1 + board_x * 2)

    def _is_key(self, key, action):
        return key in self.key_config.get(action, [])

    def handle_input(self):
        try:
            key = self.stdscr.getch()
        except:
            return False
        if key == -1:
            return False

        if self.game_over:
            if self._is_key(key, 'quit'):
                self.quit = True
                return True
            elif self._is_key(key, 'restart'):
                self.__init__(self.stdscr, self.audio, self.key_config)
                return True
            return False

        if self.paused:
            if self._is_key(key, 'pause'):
                self.paused = False
                return True
            elif self._is_key(key, 'quit'):
                self.quit = True
                return True
            return False

        if self._is_key(key, 'quit'):
            self.quit = True
            return True
        elif self._is_key(key, 'pause'):
            self.paused = True
            return True
        elif self._is_key(key, 'left'):
            return self._try_move(-1, 0)
        elif self._is_key(key, 'right'):
            return self._try_move(1, 0)
        elif self._is_key(key, 'soft_drop'):
            return self._try_move(0, 1)
        elif self._is_key(key, 'rotate_cw'):
            return self._try_rotate(clockwise=True)
        elif self._is_key(key, 'rotate_ccw'):
            return self._try_rotate(clockwise=False)
        elif self._is_key(key, 'rotate_180'):
            return self._try_rotate(rotate_180=True)
        elif self._is_key(key, 'hard_drop'):
            self._hard_drop()
            return True
        elif self._is_key(key, 'hold'):
            return self._hold_piece()

        return False

    def update(self):
        if self.game_over or self.paused or self.quit:
            return False

        piece = self.current_piece
        redraw = False

        is_on_ground = not self._is_valid_position(piece, offset_y=1)

        if is_on_ground:
            if self.lock_counter is None:
                self.lock_counter = 0
            else:
                self.lock_counter += 1
                if self.lock_counter >= self.lock_frames:
                    self._lock_piece()
                    redraw = True
        else:
            if self.lock_counter is not None:
                redraw = True
            self.lock_counter = None

            self.g_accum += self._get_gravity()
            drops = int(self.g_accum)
            if drops > 0:
                self.g_accum -= drops
                for _ in range(drops):
                    if self._is_valid_position(piece, offset_y=1):
                        piece.y += 1
                        redraw = True
                    else:
                        break

        return redraw

    def _get_shape_rgb(self, shape_name):
        return hex_to_rgb(SHAPE_RGB_COLORS[shape_name])

    def _get_color_by_index(self, color_index):
        name_index = {v: k for k, v in SHAPE_COLORS.items()}
        shape_name = name_index.get(color_index)
        if shape_name:
            return self._get_shape_rgb(shape_name)
        return (200, 200, 200)

    def _draw_block(self, y, x, color_index, is_ghost=False):
        r, g, b = self._get_color_by_index(color_index)
        a = Ansi()
        if is_ghost:
            sys.stdout.write(f'{a.cursor(y + 1, x + 1)}{a.fg(r, g, b)}{a.dim()}{DISPLAY_CHARS["ghost"]}{a.reset()}')
        else:
            sys.stdout.write(f'{a.cursor(y + 1, x + 1)}{a.fg(r, g, b)}{a.bold()}{DISPLAY_CHARS["block"]}{a.reset()}')

    def _draw_mini_piece(self, start_y, start_x, shape_name, color_index):
        r, g, b = self._get_shape_rgb(shape_name)
        a = Ansi()
        shape = SHAPES[shape_name]
        for dy, row in enumerate(shape):
            for dx, cell in enumerate(row):
                if cell:
                    sy = start_y + dy + 1
                    sx = start_x + dx * 2 + 1
                    sys.stdout.write(f'{a.cursor(sy, sx)}{a.fg(r, g, b)}{a.bold()}{DISPLAY_CHARS["block"]}{a.reset()}')

    def _safe_addstr(self, y, x, text, bold=False, dim=False, reverse=False):
        a = Ansi()
        styles = ''
        if bold:
            styles += a.bold()
        if dim:
            styles += a.dim()
        if reverse:
            styles += a.reverse()
        sys.stdout.write(f'{a.cursor(y + 1, x + 1)}{styles}{text}{a.reset()}')

    def _get_controls_text(self):
        def keys_display(action):
            keys = self.key_config.get(action, [])
            if not keys:
                return '?'
            seen = set()
            unique = []
            for k in keys:
                d = key_code_to_display(k)
                if d not in seen:
                    seen.add(d)
                    unique.append(d)
            return '/'.join(unique)

        left = keys_display('left')
        right = keys_display('right')
        soft = keys_display('soft_drop')
        cw = keys_display('rotate_cw')
        ccw = keys_display('rotate_ccw')
        r180 = keys_display('rotate_180')
        hard = keys_display('hard_drop')
        hold = keys_display('hold')
        pause = keys_display('pause')
        quit_key = keys_display('quit')

        return [
            f'{left}: Left\t{right}: Right',
            f'{soft}: Soft\t{cw}: Rot CW',
            f'{ccw}: Rot CCW\t{r180}: Rot 180',
            f'{hard}: Hard\t{hold}: Hold',
            f'{pause}: Pause\t{quit_key}: Quit'
        ]

    def draw(self):
        self.stdscr.clear()
        self.stdscr.refresh()
        sys.stdout.write(Ansi().hide_cursor())

        controls = self._get_controls_text()

        border_style = self.style.get('border', 'block')
        border_char = BORDER_STYLES.get(border_style, BORDER_STYLES['block'])

        bw = self.board_width
        bh = self.board_height
        self._safe_addstr(self.disp_y, self.disp_x,
                           border_char[0] + border_char[1] * 2 * bw + border_char[2], bold=True)
        for y in range(bh):
            self._safe_addstr(self.disp_y + 1 + y, self.disp_x, border_char[3], bold=True)
            self._safe_addstr(self.disp_y + 1 + y, self.disp_x + 1 + bw * 2, border_char[4], bold=True)
        self._safe_addstr(self.disp_y + 1 + bh, self.disp_x,
                           border_char[5] + border_char[6] * 2 * bw + border_char[7], bold=True)

        for y in range(bh):
            for x in range(bw):
                if self.board[y][x]:
                    sy, sx = self._screen_pos(y, x)
                    self._draw_block(sy, sx, self.board_colors[y][x])

        if self.current_piece and not self.game_over:
            if self._get_gravity() < 20:
                piece = self.current_piece
                for x, y in piece.get_positions():
                    if 0 <= y < bh and 0 <= x < bw and not self.board[y][x]:
                        sy, sx = self._screen_pos(self.ghost_y + (y - piece.y), x)
                        self._draw_block(sy, sx, piece.color, is_ghost=True)

        if self.current_piece and not self.game_over:
            for x, y in self.current_piece.get_positions():
                if 0 <= y < bh and 0 <= x < self.board_width:
                    sy, sx = self._screen_pos(y, x)
                    self._draw_block(sy, sx, self.current_piece.color)

        info_x = self.disp_x + 1 + bw * 2 + 4
        info_y = self.disp_y

        self._safe_addstr(info_y + 1, info_x, 'Next:', bold=True)
        self._draw_mini_piece(info_y + 3, info_x, self.next_piece_name, SHAPE_COLORS[self.next_piece_name])

        self._safe_addstr(info_y + 6, info_x, 'Hold:', bold=True)
        if self.held_piece_name:
            self._draw_mini_piece(info_y + 8, info_x, self.held_piece_name, SHAPE_COLORS[self.held_piece_name])

        game_info_y = info_y + 10
        self._safe_addstr(game_info_y + 0, info_x, f'Score: {self.score}', bold=True)
        self._safe_addstr(game_info_y + 1, info_x, f'Lines: {self.lines}', bold=True)
        self._safe_addstr(game_info_y + 2, info_x, f'Level: {self.level}', bold=True)
        g = self._get_gravity()
        self._safe_addstr(game_info_y + 3, info_x, f'Gravity: {g:.4f}', dim=True)

        for i, ctrl in enumerate(controls):
            self._safe_addstr(info_y + 16 + i, info_x, ctrl, dim=True)

        if self.paused:
            msg = ' P A U S E D '
            my = self.disp_y + 1 + bh // 2
            mx = self.disp_x + 1 + bw - len(msg) // 2
            self._safe_addstr(my, mx, msg, bold=True, reverse=True)
            self._safe_addstr(my + 1, mx - 2, 'Press P to resume', dim=True)

        if self.game_over:
            msg = 'GAME OVER'
            my = self.disp_y + 1 + bh // 2 - 1
            mx = self.disp_x + 1 + bw - len(msg) // 2 + 1
            self._safe_addstr(my, mx, msg, bold=True, reverse=True)
            self._safe_addstr(my + 1, mx - 3, f'Final Score: {self.score}', bold=True)
            self._safe_addstr(my + 2, mx - 4, 'Press R to restart', dim=True)
            self._safe_addstr(my + 3, mx - 3, 'Press Q to quit', dim=True)

        sys.stdout.flush()


    def run(self):
        try:
            if self.audio:
                self.audio.play()
            self.draw()
            frame_time = 1.0 / 60
            while not self.quit:
                frame_start = time.time()
                need_redraw = self.handle_input()
                need_redraw = self.update() or need_redraw
                if need_redraw:
                    self.draw()
                elapsed = time.time() - frame_start
                sleep_time = frame_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        finally:
            sys.stdout.write(Ansi().show_cursor())
            sys.stdout.flush()
            if self.audio:
                self.audio.stop()


def main():
    audio = AudioPlayer("./tetris.mp3")
    key_config = load_key_config()

    stdscr = curses.initscr()
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.noecho()
    curses.cbreak()
    stdscr.nodelay(True)

    try:
        game = TetrisGame(stdscr, audio, key_config)
        game.run()
    except KeyboardInterrupt:
        pass
    finally:
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        audio.stop()
        print("\n\x1b[41;30m Thanks for playing \n Terminal Tetris!   \x1b[0m\n")


if __name__ == '__main__':
    main()
