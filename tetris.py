#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Terminal Tetris - 终端俄罗斯方块 (SRS Edition)
使用 Python 内置 curses 库，无需额外依赖
支持背景音乐播放（依赖 mpv）
"""

import curses
import json
import random
import time
import os
import shutil
import subprocess
import copy

# ============ 游戏常量 ============
BOARD_WIDTH = 10
BOARD_HEIGHT = 20
PREVIEW_WIDTH = 6
PREVIEW_HEIGHT = 4

# ============ 按键 ============
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
    'left':       ['KEY_LEFT'],
    'right':      ['KEY_RIGHT'],
    'soft_drop':  ['KEY_DOWN'],
    'rotate_cw':  ['KEY_UP', 'x', 'X'],
    'rotate_ccw': ['z', 'Z'],
    'rotate_180': ['a', 'A'],
    'hard_drop':  ['SPACE'],
    'hold':       ['c', 'C'],
    'pause':      ['p', 'P'],
    'quit':       ['q', 'Q', 'ESC'],
    'restart':    ['r', 'R'],
}

CONFIG_DIR = os.path.expanduser('~/.config/terminal-tetris')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

def parse_key_name(name):
    """转换为 curses 键码"""
    if name in KEY_NAME_MAP:
        return KEY_NAME_MAP[name]
    if len(name) == 1:
        return ord(name)

    try:
        return getattr(curses, name)
    except AttributeError:
        pass

    if len(name) > 0:
        return ord(name[0])

    return 0


def load_key_config():
    """加载按键配置并且不存在的时候自动创建配置"""
    os.makedirs(CONFIG_DIR, exist_ok=True)

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            if isinstance(raw, dict) and 'key_bindings' in raw:
                raw = raw['key_bindings']
        except Exception:
            raw = None
    else:
        raw = None

    if raw is None:
        raw = DEFAULT_KEY_CONFIG_JSON
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({'key_bindings': DEFAULT_KEY_CONFIG_JSON}, f, indent=4)
                f.write('\n')
        except Exception:
            pass

    key_config = {}
    for action, keys in raw.items():
        if isinstance(keys, list):
            key_config[action] = [parse_key_name(k) for k in keys]
        else:
            key_config[action] = [parse_key_name(keys)]

    for action, default_keys in DEFAULT_KEY_CONFIG_JSON.items():
        if action not in key_config or not key_config[action]:
            key_config[action] = [parse_key_name(k) for k in default_keys]

    return key_config


# ============ SRS 旋转系统 ============
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

BLOCK_CHAR = '██'
EMPTY_CHAR = '  '
GHOST_CHAR = '▒▒'

INITIAL_SPEED = 0.8
LINES_PER_LEVEL = 10


# ============ SRS Wall Kick 数据表 ============
# 坐标: (x, y), 正x向右, 正y向上
SRS_KICKS_JLSTZ = {
    '0->R':  [(0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)],
    'R->0':  [(0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)],
    'R->2':  [(0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)],
    '2->R':  [(0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)],
    '2->L':  [(0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)],
    'L->2':  [(0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)],
    'L->0':  [(0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)],
    '0->L':  [(0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)],
}

SRS_KICKS_I = {
    '0->R':  [(0, 0), (-2, 0), (+1, 0), (-2, -1), (+1, +2)],
    'R->0':  [(0, 0), (+2, 0), (-1, 0), (+2, +1), (-1, -2)],
    'R->2':  [(0, 0), (-1, 0), (+2, 0), (-1, +2), (+2, -1)],
    '2->R':  [(0, 0), (+1, 0), (-2, 0), (+1, -2), (-2, +1)],
    '2->L':  [(0, 0), (+2, 0), (-1, 0), (+2, +1), (-1, -2)],
    'L->2':  [(0, 0), (-2, 0), (+1, 0), (-2, -1), (+1, +2)],
    'L->0':  [(0, 0), (+1, 0), (-2, 0), (+1, -2), (-2, +1)],
    '0->L':  [(0, 0), (-1, 0), (+2, 0), (-1, +2), (+2, -1)],
}

SRS_KICKS_O = {}


def hex_to_curses_rgb(hex_color):
    """把 #RRGGBB 转换 curses 的格式"""
    r = int(hex_color[1:3], 16) * 1000 // 255
    g = int(hex_color[3:5], 16) * 1000 // 255
    b = int(hex_color[5:7], 16) * 1000 // 255
    return (r, g, b)


def get_srs_kicks(shape_name, from_rot, to_rot):
    key = f"{from_rot}->{to_rot}"
    if shape_name == 'I':
        return SRS_KICKS_I.get(key, [])
    elif shape_name == 'O':
        return []
    else:
        return SRS_KICKS_JLSTZ.get(key, [])


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
        self.board_width = BOARD_WIDTH
        self.board_height = BOARD_HEIGHT
        self.board = [[0] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)]
        self.board_colors = [[0] * BOARD_WIDTH for _ in range(BOARD_HEIGHT)]
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

        self.last_drop_time = time.time()
        self.lock_delay = 0.5
        self.lock_timer = None
        self.lock_resets = 0
        self.max_lock_resets = 15

        self.stdscr.nodelay(True)
        self._init_colors()
        self.ghost_y = 0

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()

        if curses.can_change_color():
            for i, (shape_name, hex_color) in enumerate(SHAPE_RGB_COLORS.items(), 1):
                r, g, b = hex_to_curses_rgb(hex_color)
                curses.init_color(i, r, g, b)

        for i in range(1, 8):
            curses.init_pair(i, i, -1)

        curses.init_pair(8, curses.COLOR_WHITE, -1)
        curses.init_pair(9, curses.COLOR_WHITE, -1)

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

        spawn_x = self.board_width // 2 - len(SHAPES[self.next_piece_name][0]) // 2
        self.current_piece = Piece(self.next_piece_name, spawn_x, 0)
        self.next_piece_name = self._get_next_piece_name()
        self.lock_timer = None
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
            self.level = self.lines // LINES_PER_LEVEL + 1

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
            if self.lock_timer is not None and self.lock_resets < self.max_lock_resets:
                self.lock_timer = time.time()
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
                if self.lock_timer is not None and self.lock_resets < self.max_lock_resets:
                    self.lock_timer = time.time()
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
                if self.lock_timer is not None and self.lock_resets < self.max_lock_resets:
                    self.lock_timer = time.time()
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
        self.last_drop_time = time.time()

    def _hold_piece(self):
        if not self.can_hold:
            return False

        current_name = self.current_piece.shape_name

        if self.held_piece_name is None:
            self.held_piece_name = current_name
            self._spawn_piece()
        else:
            self.held_piece_name, temp = current_name, self.held_piece_name
            spawn_x = self.board_width // 2 - len(SHAPES[temp][0]) // 2
            self.current_piece = Piece(temp, spawn_x, 0)
            self.lock_timer = None
            self.lock_resets = 0
            if not self._is_valid_position(self.current_piece):
                self.game_over = True
            self._update_ghost()

        self.can_hold = False
        return True

    def _get_drop_interval(self):
        speed = INITIAL_SPEED * (0.9 ** (self.level - 1))
        return max(0.05, speed)

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
            elif key in (ord('r'), ord('R'), ord(' ')):
                self.__init__(self.stdscr, self.audio, self.key_config)
                return True
            return False

        if self.paused:
            if self._is_key(key, 'pause') or key == ord(' '):
                self.paused = False
                self.last_drop_time = time.time()
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

        now = time.time()
        piece = self.current_piece
        redraw = False

        is_on_ground = not self._is_valid_position(piece, offset_y=1)

        if is_on_ground:
            if self.lock_timer is None:
                self.lock_timer = now
            elif now - self.lock_timer >= self.lock_delay:
                self._lock_piece()
                self.last_drop_time = now
                redraw = True
        else:
            if self.lock_timer is not None:
                redraw = True
            self.lock_timer = None
            if now - self.last_drop_time >= self._get_drop_interval():
                if self._is_valid_position(piece, offset_y=1):
                    piece.y += 1
                    self._update_ghost()
                    redraw = True
                self.last_drop_time = now

        return redraw

    def _draw_block(self, y, x, color_pair, is_ghost=False):
        try:
            if is_ghost:
                self.stdscr.addstr(y, x, GHOST_CHAR, curses.color_pair(color_pair) | curses.A_DIM)
            else:
                self.stdscr.addstr(y, x, BLOCK_CHAR, curses.color_pair(color_pair) | curses.A_BOLD)
        except curses.error:
            pass

    def _draw_mini_piece(self, start_y, start_x, shape_name, color):
        shape = SHAPES[shape_name]
        for dy, row in enumerate(shape):
            for dx, cell in enumerate(row):
                if cell:
                    try:
                        self.stdscr.addstr(start_y + dy, start_x + dx * 2, BLOCK_CHAR,
                                         curses.color_pair(color) | curses.A_BOLD)
                    except:
                        pass

    def _safe_addstr(self, y, x, text, attr=0):
        """安全的 addstr，越界时静默忽略"""
        try:
            self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass

    def draw(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        # 动态计算最小高度需求
        controls = [
            'A/< : Left   D/> : Right',
            'S/v : Soft   W/^ : Rot CW',
            'Z/J : Rot CCW  X/K : 180',
            'Space: Hard   C/H : Hold',
            'P: Pause      Q/ESC: Quit'
        ]
        # info_y=1, controls 从 info_y+13 开始 (Next+Hold+Score 占 12 行)
        # 最后一行在 1 + 13 + len(controls) = 14 + 5 = 19
        # 加上 board 底部在 1 + 1 + 20 = 22, 所以 min_height = max(22, 19) + 2 = 24
        min_height_needed = max(BOARD_HEIGHT + 4, 14 + len(controls) + 2)
        min_width_needed = (BOARD_WIDTH + PREVIEW_WIDTH + 6) * 2 + 4

        if height < min_height_needed or width < min_width_needed:
            msg = f"Terminal too small! Need {min_width_needed}x{min_height_needed}, got {width}x{height}"
            self._safe_addstr(0, 0, msg[:width-1])
            self.stdscr.refresh()
            return

        border_color = curses.A_BOLD
        self._safe_addstr(self.disp_y, self.disp_x,
                           '╔' + '══' * BOARD_WIDTH + '╗', border_color)
        for y in range(BOARD_HEIGHT):
            self._safe_addstr(self.disp_y + 1 + y, self.disp_x, '║', border_color)
            self._safe_addstr(self.disp_y + 1 + y, self.disp_x + 1 + BOARD_WIDTH * 2, '║', border_color)
        self._safe_addstr(self.disp_y + 1 + BOARD_HEIGHT, self.disp_x,
                           '╚' + '══' * BOARD_WIDTH + '╝', border_color)

        for y in range(BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                if self.board[y][x]:
                    sy, sx = self._screen_pos(y, x)
                    self._draw_block(sy, sx, self.board_colors[y][x])

        if self.current_piece and not self.game_over:
            piece = self.current_piece
            for x, y in piece.get_positions():
                if 0 <= y < BOARD_HEIGHT and 0 <= x < BOARD_WIDTH and not self.board[y][x]:
                    sy, sx = self._screen_pos(self.ghost_y + (y - piece.y), x)
                    self._draw_block(sy, sx, piece.color, is_ghost=True)

        if self.current_piece and not self.game_over:
            for x, y in self.current_piece.get_positions():
                if 0 <= y < BOARD_HEIGHT and 0 <= x < self.board_width:
                    sy, sx = self._screen_pos(y, x)
                    self._draw_block(sy, sx, self.current_piece.color)

        info_x = self.disp_x + 1 + BOARD_WIDTH * 2 + 3
        info_y = self.disp_y

        self._safe_addstr(info_y, info_x, '  T E T R I S  ', curses.A_BOLD)

        # Next piece
        self._safe_addstr(info_y + 2, info_x, 'Next:', curses.A_BOLD)
        self._draw_mini_piece(info_y + 3, info_x, self.next_piece_name, SHAPE_COLORS[self.next_piece_name])

        # Hold piece
        self._safe_addstr(info_y + 8, info_x, 'Hold:', curses.A_BOLD)
        if self.held_piece_name:
            self._draw_mini_piece(info_y + 9, info_x, self.held_piece_name, SHAPE_COLORS[self.held_piece_name])
        else:
            self._safe_addstr(info_y + 9, info_x, '---', curses.A_DIM)

        self._safe_addstr(info_y + 14, info_x, f'Score: {self.score}', curses.A_BOLD)
        self._safe_addstr(info_y + 15, info_x, f'Lines: {self.lines}', curses.A_BOLD)
        self._safe_addstr(info_y + 16, info_x, f'Level: {self.level}', curses.A_BOLD)

        speed = self._get_drop_interval()
        self._safe_addstr(info_y + 17, info_x, f'Speed: {speed:.2f}s', curses.A_DIM)

        self._safe_addstr(info_y + 19, info_x, 'Controls:', curses.A_BOLD | curses.A_UNDERLINE)
        for i, ctrl in enumerate(controls):
            self._safe_addstr(info_y + 20 + i, info_x, ctrl, curses.A_DIM)

        if self.paused:
            msg = ' P A U S E D '
            my = self.disp_y + 1 + BOARD_HEIGHT // 2
            mx = self.disp_x + 1 + BOARD_WIDTH - len(msg) // 2
            self._safe_addstr(my, mx, msg, curses.A_BOLD | curses.A_REVERSE)
            self._safe_addstr(my + 1, mx - 2, 'Press P to resume', curses.A_DIM)

        if self.game_over:
            msg = 'GAME OVER'
            my = self.disp_y + 1 + BOARD_HEIGHT // 2 - 1
            mx = self.disp_x + 1 + BOARD_WIDTH - len(msg) // 2 + 1
            self._safe_addstr(my, mx, msg, curses.A_BOLD | curses.A_REVERSE)
            self._safe_addstr(my + 1, mx - 3, f'Final Score: {self.score}', curses.A_BOLD)
            self._safe_addstr(my + 2, mx - 4, 'Press R to restart', curses.A_DIM)
            self._safe_addstr(my + 3, mx - 3, 'Press Q to quit', curses.A_DIM)

        self.stdscr.refresh()

    def run(self):
        try:
            if self.audio:
                self.audio.play()
            self.draw()
            while not self.quit:
                need_draw = self.handle_input() or self.update()
                if need_draw:
                    self.draw()
                time.sleep(0.05)
        finally:
            if self.audio:
                self.audio.stop()


def main():
    audio = AudioPlayer("./tetris.mp3")
    key_config = load_key_config()
    def wrapper(stdscr):
        curses.curs_set(0)
        stdscr.keypad(True)
        curses.noecho()

        game = TetrisGame(stdscr, audio, key_config)
        game.run()

    try:
        curses.wrapper(wrapper)
    except KeyboardInterrupt:
        pass
    finally:
        audio.stop()
    print("Thanks for playing Terminal Tetris!")


if __name__ == '__main__':
    main()
