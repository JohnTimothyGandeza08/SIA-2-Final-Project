# games_page.py
import random
import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont


# ==========================================
# GAME 1: BEAT CATCHER (4-LANE RHYTHM)
# ==========================================
class BeatCatcherCanvas(QWidget):
    LANE_KEYS = [Qt.Key_D, Qt.Key_F, Qt.Key_J, Qt.Key_K]
    LANE_LABELS = ["D", "F", "J", "K"]
    LANE_COLORS = ["#0055ff", "#00b4ff", "#8a5cff", "#ff4d6d"]

    def __init__(self, on_stats_changed, parent=None):
        super().__init__(parent)
        self.on_stats_changed = on_stats_changed
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(520, 440)

        self.notes = []  # dicts: lane, y, speed, hit
        self.pressed_lanes = set()
        self.lane_flash = [0.0, 0.0, 0.0, 0.0]
        self.feedback_text = ""
        self.feedback_color = "#ffffff"
        self.feedback_timer = 0.0

        self.score = 0
        self.best_score = 0
        self.combo = 0
        self.lives = 5
        self.running = False
        self.paused = False
        self.game_over = False

        self._spawn_accum = 0.0
        self._elapsed = 0.0
        self._last_tick = time.monotonic()

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)

    def start_game(self):
        self.notes.clear()
        self.pressed_lanes.clear()
        self.lane_flash = [0.0, 0.0, 0.0, 0.0]
        self.feedback_text = ""
        self.score = 0
        self.combo = 0
        self.lives = 5
        self.running = True
        self.paused = False
        self.game_over = False
        self._spawn_accum = 0.35
        self._elapsed = 0.0
        self._last_tick = time.monotonic()
        self.timer.start()
        self.setFocus()
        self.on_stats_changed()
        self.update()

    def toggle_pause(self):
        if not self.running or self.game_over:
            return
        self.paused = not self.paused
        if self.paused:
            self.timer.stop()
        else:
            self._last_tick = time.monotonic()
            self.timer.start()
            self.setFocus()
        self.on_stats_changed()
        self.update()

    def pause_if_running(self):
        if self.running and not self.paused and not self.game_over:
            self.paused = True
            self.timer.stop()
            self.on_stats_changed()
            self.update()

    def _hit_line_y(self):
        return self.height() - 68

    def _board_rect(self):
        board_w = min(440, self.width() - 40)
        left = (self.width() - board_w) / 2
        return QRectF(left, 12, board_w, self.height() - 24)

    def _tick(self):
        now = time.monotonic()
        dt = min(now - self._last_tick, 0.05)
        self._last_tick = now
        self._elapsed += dt

        # Gradually speed up spawns and note velocity
        spawn_interval = max(0.28, 0.68 - self._elapsed * 0.006)
        note_speed = min(430.0, 220.0 + self._elapsed * 3.5)

        self._spawn_accum += dt
        if self._spawn_accum >= spawn_interval:
            self._spawn_accum = 0.0
            lane = random.randint(0, 3)
            self.notes.append({
                "lane": lane,
                "y": 24.0,
                "speed": note_speed,
            })

        hit_y = self._hit_line_y()
        remaining = []
        for note in self.notes:
            note["y"] += note["speed"] * dt
            if note["y"] > hit_y + 52:
                self._register_miss("MISS")
                if self.game_over:
                    return
            else:
                remaining.append(note)
        self.notes = remaining

        for i in range(4):
            if self.lane_flash[i] > 0:
                self.lane_flash[i] = max(0.0, self.lane_flash[i] - dt * 4.0)
        if self.feedback_timer > 0:
            self.feedback_timer = max(0.0, self.feedback_timer - dt)

        self.update()

    def _register_miss(self, label):
        self.combo = 0
        self.lives -= 1
        self.feedback_text = label
        self.feedback_color = "#ff5555"
        self.feedback_timer = 0.65
        if self.lives <= 0:
            self.lives = 0
            self.running = False
            self.game_over = True
            self.timer.stop()
        self.on_stats_changed()
        self.update()

    def _trigger_lane(self, lane):
        if not self.running or self.paused or self.game_over:
            return
        self.lane_flash[lane] = 1.0
        hit_y = self._hit_line_y()

        best_idx = None
        best_dist = 9999.0
        for idx, note in enumerate(self.notes):
            if note["lane"] == lane:
                dist = abs(note["y"] - hit_y)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx

        if best_idx is not None and best_dist <= 46:
            self.notes.pop(best_idx)
            self.combo += 1
            mult = 1 + (self.combo // 10)
            if best_dist <= 22:
                self.score += 100 * mult
                self.feedback_text = f"PERFECT! x{mult}" if mult > 1 else "PERFECT!"
                self.feedback_color = "#00e5ff"
            else:
                self.score += 50 * mult
                self.feedback_text = f"GOOD x{mult}" if mult > 1 else "GOOD"
                self.feedback_color = "#6ee7b7"
            if self.score > self.best_score:
                self.best_score = self.score
            self.feedback_timer = 0.55
            self.on_stats_changed()
        else:
            self._register_miss("MISS")
        self.update()

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key in self.LANE_KEYS:
            lane = self.LANE_KEYS.index(key)
            self.pressed_lanes.add(lane)
            self._trigger_lane(lane)
            event.accept()
            return
        if key == Qt.Key_Space:
            if not self.running or self.game_over:
                self.start_game()
            else:
                self.toggle_pause()
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key in self.LANE_KEYS:
            self.pressed_lanes.discard(self.LANE_KEYS.index(key))
            self.update()
            event.accept()
            return
        super().keyReleaseEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.LeftButton:
            if not self.running or self.game_over:
                self.start_game()
                return
            rect = self._board_rect()
            if rect.contains(event.position()):
                lane_w = rect.width() / 4.0
                lane = int((event.position().x() - rect.left()) / lane_w)
                lane = max(0, min(3, lane))
                self._trigger_lane(lane)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self._board_rect()
        lane_w = rect.width() / 4.0
        hit_y = self._hit_line_y()

        # Board background
        p.setPen(QPen(QColor("#262626"), 1))
        p.setBrush(QBrush(QColor("#101014")))
        p.drawRoundedRect(rect, 10, 10)

        # Lanes + flash
        for i in range(4):
            lx = rect.left() + i * lane_w
            lane_rect = QRectF(lx, rect.top(), lane_w, rect.height())
            if self.lane_flash[i] > 0 or i in self.pressed_lanes:
                alpha = int(max(self.lane_flash[i], 0.45 if i in self.pressed_lanes else 0.0) * 65)
                c = QColor(self.LANE_COLORS[i])
                c.setAlpha(alpha)
                p.fillRect(lane_rect, c)

            if i > 0:
                p.setPen(QPen(QColor("#1e1e26"), 1))
                p.drawLine(int(lx), int(rect.top()), int(lx), int(rect.bottom()))

        # Hit target line & lane pads
        p.setPen(QPen(QColor("#3a3a4a"), 2))
        p.drawLine(int(rect.left() + 8), int(hit_y), int(rect.right() - 8), int(hit_y))

        for i in range(4):
            lx = rect.left() + i * lane_w
            pad_rect = QRectF(lx + 10, hit_y - 16, lane_w - 20, 32)
            active = i in self.pressed_lanes or self.lane_flash[i] > 0.2
            pad_color = QColor(self.LANE_COLORS[i]) if active else QColor("#1c1c24")
            p.setPen(QPen(QColor(self.LANE_COLORS[i]), 2))
            p.setBrush(QBrush(pad_color))
            p.drawRoundedRect(pad_rect, 8, 8)

            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 11, QFont.Bold))
            p.drawText(pad_rect, Qt.AlignCenter, self.LANE_LABELS[i])

        # Falling notes
        for note in self.notes:
            lane = note["lane"]
            lx = rect.left() + lane * lane_w
            note_rect = QRectF(lx + 14, note["y"] - 11, lane_w - 28, 22)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(self.LANE_COLORS[lane])))
            p.drawRoundedRect(note_rect, 7, 7)

        # Judgment feedback
        if self.feedback_timer > 0 and self.feedback_text:
            p.setPen(QColor(self.feedback_color))
            p.setFont(QFont("Segoe UI", 15, QFont.Bold))
            p.drawText(QRectF(rect.left(), hit_y - 72, rect.width(), 32), Qt.AlignCenter, self.feedback_text)

        # Start / Pause / Game Over overlay
        if not self.running or self.paused or self.game_over:
            overlay = QColor(8, 8, 12, 195)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(overlay))
            p.drawRoundedRect(rect, 10, 10)

            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 20, QFont.Bold))
            if self.game_over:
                title = "GAME OVER"
                sub = f"Score: {self.score}   ·   Best: {self.best_score}\nPress Space or Click to Play Again"
            elif self.paused:
                title = "PAUSED"
                sub = "Press Space or Click Resume"
            else:
                title = "BEAT CATCHER"
                sub = "Press D · F · J · K (or click lanes) as notes reach the bar\nPress Space or Click Start"
            p.drawText(QRectF(rect.left(), rect.center().y() - 55, rect.width(), 40), Qt.AlignCenter, title)
            p.setPen(QColor("#aaaaaa"))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(QRectF(rect.left() + 20, rect.center().y() - 8, rect.width() - 40, 60), Qt.AlignCenter, sub)


class BeatCatcherWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hud = QFrame()
        hud.setObjectName("TableContainer")
        hud_layout = QHBoxLayout(hud)
        hud_layout.setContentsMargins(16, 10, 16, 10)
        hud_layout.setSpacing(20)

        self.score_lbl = QLabel("Score: 0")
        self.score_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        self.combo_lbl = QLabel("Combo: 0")
        self.combo_lbl.setStyleSheet("color: #00b4ff; font-size: 13px; font-weight: bold;")
        self.lives_lbl = QLabel("Lives: ♥♥♥♥♥")
        self.lives_lbl.setStyleSheet("color: #ff5555; font-size: 13px; font-weight: bold;")
        self.best_lbl = QLabel("Best: 0")
        self.best_lbl.setStyleSheet("color: #aaa; font-size: 12px;")

        self.start_btn = QPushButton("Start")
        self.start_btn.setFocusPolicy(Qt.NoFocus)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet("background-color: #0055ff; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold;")

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setFocusPolicy(Qt.NoFocus)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setStyleSheet("background-color: #242424; color: white; border: none; border-radius: 6px; padding: 6px 14px;")

        self.canvas = BeatCatcherCanvas(self._update_hud)
        self.start_btn.clicked.connect(self.canvas.start_game)
        self.pause_btn.clicked.connect(self.canvas.toggle_pause)

        hud_layout.addWidget(self.score_lbl)
        hud_layout.addWidget(self.combo_lbl)
        hud_layout.addWidget(self.lives_lbl)
        hud_layout.addWidget(self.best_lbl)
        hud_layout.addStretch()
        hud_layout.addWidget(self.pause_btn)
        hud_layout.addWidget(self.start_btn)

        layout.addWidget(hud)
        layout.addWidget(self.canvas, 1)

    def _update_hud(self):
        self.score_lbl.setText(f"Score: {self.canvas.score}")
        self.combo_lbl.setText(f"Combo: {self.canvas.combo}")
        hearts = "♥" * self.canvas.lives + "♡" * (5 - self.canvas.lives)
        self.lives_lbl.setText(f"Lives: {hearts}")
        self.best_lbl.setText(f"Best: {self.canvas.best_score}")
        self.start_btn.setText("Restart" if self.canvas.running or self.canvas.game_over else "Start")
        self.pause_btn.setText("Resume" if self.canvas.paused else "Pause")

    def pause_game(self):
        self.canvas.pause_if_running()


# ==========================================
# GAME 2: NEON SNAKE
# ==========================================
class SnakeCanvas(QWidget):
    COLS = 22
    ROWS = 16

    def __init__(self, on_stats_changed, parent=None):
        super().__init__(parent)
        self.on_stats_changed = on_stats_changed
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(520, 440)

        self.snake = [(11, 8), (10, 8), (9, 8)]
        self.direction = (1, 0)
        self.dir_queue = []
        self.food = (16, 8)
        self.score = 0
        self.best_score = 0
        self.running = False
        self.paused = False
        self.game_over = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)

    def start_game(self):
        self.snake = [(11, 8), (10, 8), (9, 8)]
        self.direction = (1, 0)
        self.dir_queue.clear()
        self.score = 0
        self.running = True
        self.paused = False
        self.game_over = False
        self._spawn_food()
        self.timer.start(125)
        self.setFocus()
        self.on_stats_changed()
        self.update()

    def toggle_pause(self):
        if not self.running or self.game_over:
            return
        self.paused = not self.paused
        if self.paused:
            self.timer.stop()
        else:
            self.timer.start(self._current_interval())
            self.setFocus()
        self.on_stats_changed()
        self.update()

    def pause_if_running(self):
        if self.running and not self.paused and not self.game_over:
            self.paused = True
            self.timer.stop()
            self.on_stats_changed()
            self.update()

    def _current_interval(self):
        return max(70, 125 - (self.score // 30) * 5)

    def _spawn_food(self):
        occupied = set(self.snake)
        free = [(x, y) for x in range(self.COLS) for y in range(self.ROWS) if (x, y) not in occupied]
        if free:
            self.food = random.choice(free)

    def _step(self):
        if self.dir_queue:
            self.direction = self.dir_queue.pop(0)

        hx, hy = self.snake[0]
        dx, dy = self.direction
        nx, ny = hx + dx, hy + dy

        if nx < 0 or nx >= self.COLS or ny < 0 or ny >= self.ROWS or (nx, ny) in self.snake[:-1]:
            self.running = False
            self.game_over = True
            self.timer.stop()
            self.on_stats_changed()
            self.update()
            return

        self.snake.insert(0, (nx, ny))
        if (nx, ny) == self.food:
            self.score += 10
            if self.score > self.best_score:
                self.best_score = self.score
            self._spawn_food()
            self.timer.setInterval(self._current_interval())
            self.on_stats_changed()
        else:
            self.snake.pop()

        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        mapping = {
            Qt.Key_Up: (0, -1), Qt.Key_W: (0, -1),
            Qt.Key_Down: (0, 1), Qt.Key_S: (0, 1),
            Qt.Key_Left: (-1, 0), Qt.Key_A: (-1, 0),
            Qt.Key_Right: (1, 0), Qt.Key_D: (1, 0),
        }
        if key in mapping:
            new_dir = mapping[key]
            last_dir = self.dir_queue[-1] if self.dir_queue else self.direction
            if new_dir != last_dir and (new_dir[0] != -last_dir[0] or new_dir[1] != -last_dir[1]):
                if len(self.dir_queue) < 2:
                    self.dir_queue.append(new_dir)
            event.accept()
            return
        if key == Qt.Key_Space:
            if not self.running or self.game_over:
                self.start_game()
            else:
                self.toggle_pause()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        if event.button() == Qt.LeftButton and (not self.running or self.game_over):
            self.start_game()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cell = min((self.width() - 40) / self.COLS, (self.height() - 24) / self.ROWS)
        board_w = cell * self.COLS
        board_h = cell * self.ROWS
        left = (self.width() - board_w) / 2
        top = (self.height() - board_h) / 2
        board = QRectF(left, top, board_w, board_h)

        # Board & grid
        p.setPen(QPen(QColor("#262626"), 1))
        p.setBrush(QBrush(QColor("#101014")))
        p.drawRoundedRect(board, 8, 8)

        p.setPen(QPen(QColor("#1a1a22"), 1))
        for c in range(1, self.COLS):
            x = left + c * cell
            p.drawLine(int(x), int(top), int(x), int(top + board_h))
        for r in range(1, self.ROWS):
            y = top + r * cell
            p.drawLine(int(left), int(y), int(left + board_w), int(y))

        # Food
        fx, fy = self.food
        food_rect = QRectF(left + fx * cell + 3, top + fy * cell + 3, cell - 6, cell - 6)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor("#ff4d6d")))
        p.drawEllipse(food_rect)

        # Snake
        for idx, (sx, sy) in enumerate(self.snake):
            seg_rect = QRectF(left + sx * cell + 2, top + sy * cell + 2, cell - 4, cell - 4)
            color = QColor("#00b4ff") if idx == 0 else QColor("#0055ff")
            p.setBrush(QBrush(color))
            p.drawRoundedRect(seg_rect, 5, 5)

        if not self.running or self.paused or self.game_over:
            p.setBrush(QBrush(QColor(8, 8, 12, 195)))
            p.drawRoundedRect(board, 8, 8)
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 20, QFont.Bold))
            if self.game_over:
                title = "GAME OVER"
                sub = f"Score: {self.score}   ·   Best: {self.best_score}\nPress Space or Click to Play Again"
            elif self.paused:
                title = "PAUSED"
                sub = "Press Space or Click Resume"
            else:
                title = "NEON SNAKE"
                sub = "Use Arrow Keys or WASD to move\nPress Space or Click Start"
            p.drawText(QRectF(board.left(), board.center().y() - 55, board.width(), 40), Qt.AlignCenter, title)
            p.setPen(QColor("#aaaaaa"))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(QRectF(board.left() + 20, board.center().y() - 8, board.width() - 40, 60), Qt.AlignCenter, sub)


class SnakeGameWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hud = QFrame()
        hud.setObjectName("TableContainer")
        hud_layout = QHBoxLayout(hud)
        hud_layout.setContentsMargins(16, 10, 16, 10)
        hud_layout.setSpacing(20)

        self.score_lbl = QLabel("Score: 0")
        self.score_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        self.best_lbl = QLabel("Best: 0")
        self.best_lbl.setStyleSheet("color: #aaa; font-size: 12px;")

        self.start_btn = QPushButton("Start")
        self.start_btn.setFocusPolicy(Qt.NoFocus)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet("background-color: #0055ff; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold;")

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setFocusPolicy(Qt.NoFocus)
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.setStyleSheet("background-color: #242424; color: white; border: none; border-radius: 6px; padding: 6px 14px;")

        self.canvas = SnakeCanvas(self._update_hud)
        self.start_btn.clicked.connect(self.canvas.start_game)
        self.pause_btn.clicked.connect(self.canvas.toggle_pause)

        hud_layout.addWidget(self.score_lbl)
        hud_layout.addWidget(self.best_lbl)
        hud_layout.addStretch()
        hud_layout.addWidget(self.pause_btn)
        hud_layout.addWidget(self.start_btn)

        layout.addWidget(hud)
        layout.addWidget(self.canvas, 1)

    def _update_hud(self):
        self.score_lbl.setText(f"Score: {self.canvas.score}")
        self.best_lbl.setText(f"Best: {self.canvas.best_score}")
        self.start_btn.setText("Restart" if self.canvas.running or self.canvas.game_over else "Start")
        self.pause_btn.setText("Resume" if self.canvas.paused else "Pause")

    def pause_game(self):
        self.canvas.pause_if_running()


# ==========================================
# GAME 3: SOUND MATCH (MEMORY CARDS)
# ==========================================
class MemoryMatchWidget(QWidget):
    SYMBOLS = ["♪", "♫", "♯", "♭", "★", "◆", "▲", "●"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self.buttons = []
        self.flipped = []
        self.matched = set()
        self.moves = 0
        self.best_moves = None
        self.seconds = 0
        self.locked = False

        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self._tick_clock)

        self.mismatch_timer = QTimer(self)
        self.mismatch_timer.setSingleShot(True)
        self.mismatch_timer.setInterval(650)
        self.mismatch_timer.timeout.connect(self._hide_mismatched)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        hud = QFrame()
        hud.setObjectName("TableContainer")
        hud_layout = QHBoxLayout(hud)
        hud_layout.setContentsMargins(16, 10, 16, 10)
        hud_layout.setSpacing(20)

        self.pairs_lbl = QLabel("Pairs: 0/8")
        self.pairs_lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")
        self.moves_lbl = QLabel("Moves: 0")
        self.moves_lbl.setStyleSheet("color: #00b4ff; font-size: 13px; font-weight: bold;")
        self.time_lbl = QLabel("Time: 00:00")
        self.time_lbl.setStyleSheet("color: #aaa; font-size: 12px;")
        self.best_lbl = QLabel("Best: --")
        self.best_lbl.setStyleSheet("color: #aaa; font-size: 12px;")

        new_btn = QPushButton("New Game")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet("background-color: #0055ff; color: white; border: none; border-radius: 6px; padding: 6px 14px; font-weight: bold;")
        new_btn.clicked.connect(self.new_game)

        hud_layout.addWidget(self.pairs_lbl)
        hud_layout.addWidget(self.moves_lbl)
        hud_layout.addWidget(self.time_lbl)
        hud_layout.addWidget(self.best_lbl)
        hud_layout.addStretch()
        hud_layout.addWidget(new_btn)
        layout.addWidget(hud)

        board_wrap = QHBoxLayout()
        board_wrap.addStretch()
        grid_frame = QFrame()
        grid_frame.setObjectName("TableContainer")
        grid = QGridLayout(grid_frame)
        grid.setContentsMargins(18, 18, 18, 18)
        grid.setSpacing(12)

        for i in range(16):
            btn = QPushButton("?")
            btn.setFixedSize(92, 92)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._on_card_clicked(idx))
            grid.addWidget(btn, i // 4, i % 4)
            self.buttons.append(btn)

        board_wrap.addWidget(grid_frame)
        board_wrap.addStretch()
        layout.addLayout(board_wrap)

        self.status_lbl = QLabel("Flip two cards to match all 8 pairs.")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.status_lbl)
        layout.addStretch()

        self.new_game()

    def new_game(self):
        self.mismatch_timer.stop()
        self.clock_timer.stop()
        self.cards = self.SYMBOLS * 2
        random.shuffle(self.cards)
        self.flipped.clear()
        self.matched.clear()
        self.moves = 0
        self.seconds = 0
        self.locked = False
        self.status_lbl.setText("Flip two cards to match all 8 pairs.")
        self.status_lbl.setStyleSheet("color: #888; font-size: 12px;")
        self._refresh_cards()
        self._update_hud()

    def _tick_clock(self):
        self.seconds += 1
        self._update_hud()

    def _update_hud(self):
        self.pairs_lbl.setText(f"Pairs: {len(self.matched) // 2}/8")
        self.moves_lbl.setText(f"Moves: {self.moves}")
        self.time_lbl.setText(f"Time: {self.seconds // 60:02d}:{self.seconds % 60:02d}")
        self.best_lbl.setText(f"Best: {self.best_moves} moves" if self.best_moves is not None else "Best: --")

    def _refresh_cards(self):
        for i, btn in enumerate(self.buttons):
            if i in self.matched:
                btn.setText(self.cards[i])
                btn.setStyleSheet(
                    "background-color: #0055ff; color: white; border: none; "
                    "border-radius: 10px; font-size: 28px; font-weight: bold;"
                )
            elif i in self.flipped:
                btn.setText(self.cards[i])
                btn.setStyleSheet(
                    "background-color: #242430; color: #00b4ff; border: 2px solid #0055ff; "
                    "border-radius: 10px; font-size: 28px; font-weight: bold;"
                )
            else:
                btn.setText("?")
                btn.setStyleSheet(
                    "QPushButton { background-color: #18181c; color: #555; border: 1px solid #2b2b35; "
                    "border-radius: 10px; font-size: 22px; font-weight: bold; }"
                    "QPushButton:hover { background-color: #222228; color: #888; }"
                )

    def _on_card_clicked(self, idx):
        if self.locked or idx in self.matched or idx in self.flipped:
            return
        if not self.clock_timer.isActive() and len(self.matched) < 16:
            self.clock_timer.start()

        self.flipped.append(idx)
        self._refresh_cards()

        if len(self.flipped) == 2:
            self.moves += 1
            a, b = self.flipped
            if self.cards[a] == self.cards[b]:
                self.matched.update((a, b))
                self.flipped.clear()
                self._refresh_cards()
                if len(self.matched) == 16:
                    self.clock_timer.stop()
                    if self.best_moves is None or self.moves < self.best_moves:
                        self.best_moves = self.moves
                    self.status_lbl.setText(f"You cleared all pairs in {self.moves} moves!")
                    self.status_lbl.setStyleSheet("color: #6ee7b7; font-size: 13px; font-weight: bold;")
            else:
                self.locked = True
                self.mismatch_timer.start()
            self._update_hud()

    def _hide_mismatched(self):
        self.flipped.clear()
        self.locked = False
        self._refresh_cards()

    def pause_game(self):
        self.clock_timer.stop()


# ==========================================
# GAMES HUB PAGE
# ==========================================
class GamesPage(QWidget):
    def __init__(self, username="User", parent=None):
        super().__init__(parent)
        self.username = username
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(16)

        # --- WELCOME MESSAGE ---
        welcome_lbl = QLabel(f"Welcome, {self.username}!")
        welcome_lbl.setStyleSheet("color: #0055ff; font-size: 18px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(welcome_lbl)

        # Header + Game Switcher
        top_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("Pulse Arcade")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        subtitle = QLabel("Play mini-games while your music keeps playing")
        subtitle.setStyleSheet("color: #888; font-size: 11px;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        top_row.addLayout(title_col)
        top_row.addStretch()

        self.game_tabs = []
        for idx, name in enumerate(["Beat Catcher", "Neon Snake", "Sound Match"]):
            btn = QPushButton(name)
            btn.setFixedHeight(32)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self.select_game(i))
            top_row.addWidget(btn)
            self.game_tabs.append(btn)

        layout.addLayout(top_row)

        self.stack = QStackedWidget()
        self.games = [
            BeatCatcherWidget(),
            SnakeGameWidget(),
            MemoryMatchWidget(),
        ]
        for g in self.games:
            self.stack.addWidget(g)

        layout.addWidget(self.stack, 1)
        self.select_game(0)

    def select_game(self, index):
        self.pause_all()
        self.stack.setCurrentIndex(index)

        active_style = (
            "QPushButton { background-color: #ffffff; color: #000000; border: none; "
            "border-radius: 16px; padding: 6px 16px; font-size: 12px; font-weight: bold; }"
        )
        inactive_style = (
            "QPushButton { background-color: #242424; color: #ffffff; border: none; "
            "border-radius: 16px; padding: 6px 16px; font-size: 12px; }"
            "QPushButton:hover { background-color: #333333; }"
        )
        for i, btn in enumerate(self.game_tabs):
            btn.setStyleSheet(active_style if i == index else inactive_style)

    def pause_all(self):
        for g in self.games:
            g.pause_game()