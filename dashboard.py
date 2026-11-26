# dashboard.py
import sys
import random
import requests
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QSlider, QGridLayout, QStackedWidget, QSizePolicy, QMessageBox,
    QDialog, QComboBox, QMenu
)
from PySide6.QtCore import Qt, QPointF, QUrl, QThread, Signal, QByteArray, QTimer, QSize, QRectF, QObject
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPixmap, QImage, QIcon, QPen, QPainterPath
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from theme import DARK_THEME
import jamendo_api
from games_api import fetch_cartoon_images, fetch_random_pokemon, fetch_random_names, fetch_questions
from video_api import VideoSearchClient, PixabayVideoClient


# ======================================================================
# GAMES: BASE CLASS (formerly games/base_game.py)
# ======================================================================
class BaseGame(QWidget):
    """Every game must emit this signal when the user wants to return to the menu."""
    back_requested = Signal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

    def start(self):
        """Override this method to load data and initialise the game."""
        raise NotImplementedError


# ======================================================================
# GAMES: TRIVIA (formerly games/trivia_game.py)
# ======================================================================
class TriviaGame(BaseGame):
    def __init__(self):
        super().__init__()
        self.questions = []
        self.current_index = 0
        self.score = 0

        self.layout.addStretch()

        self.question_label = QLabel("Loading question...")
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(Qt.AlignCenter)
        self.question_label.setStyleSheet("font-size: 22px; font-weight: bold; margin-bottom: 20px;")
        self.layout.addWidget(self.question_label)

        self.answer_layout = QVBoxLayout()
        self.answer_layout.setSpacing(15)
        self.answer_layout.setAlignment(Qt.AlignCenter)  # Center the buttons
        self.answer_buttons = []
        for _ in range(4):
            btn = QPushButton()
            btn.setFixedSize(400, 50)  # Fixed size looks much better
            btn.setStyleSheet("font-size: 16px; border-radius: 8px;")
            btn.clicked.connect(self.check_answer)
            self.answer_layout.addWidget(btn, alignment=Qt.AlignCenter)
            self.answer_buttons.append(btn)
        self.layout.addLayout(self.answer_layout)

        self.score_label = QLabel("Score: 0")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-top: 30px; color: #89b4fa;")
        self.layout.addWidget(self.score_label)

        self.layout.addStretch()

        back_btn = QPushButton("← Back to Menu")
        back_btn.setFixedWidth(200)
        back_btn.clicked.connect(self.back_requested.emit)
        self.layout.addWidget(back_btn, alignment=Qt.AlignCenter)

    def start(self):
        try:
            self.questions = fetch_questions(amount=5)
        except Exception as e:
            QMessageBox.critical(self, "API Error", str(e))
            return
        self.current_index = 0
        self.score = 0
        self.show_question()

    def show_question(self):
        if self.current_index >= len(self.questions):
            QMessageBox.information(self, "Finished", f"Final score: {self.score}/{len(self.questions)}")
            self.back_requested.emit()
            return

        q = self.questions[self.current_index]
        self.question_label.setText(f"Q{self.current_index + 1}: {q['question']}")

        answers = [q["correct_answer"]] + q["incorrect_answers"]
        random.shuffle(answers)

        for btn, ans in zip(self.answer_buttons, answers):
            btn.setText(ans)
            btn.setEnabled(True)
            btn.setStyleSheet("")  # Reset styles
            btn.setProperty("is_correct", ans == q["correct_answer"])

    def check_answer(self):
        btn = self.sender()
        is_correct = btn.property("is_correct")

        # Visual Feedback
        if is_correct:
            self.score += 1
            btn.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold;")
        else:
            btn.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold;")
            # Highlight the correct one
            for b in self.answer_buttons:
                if b.property("is_correct"):
                    b.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold;")

        self.score_label.setText(f"Score: {self.score}")

        for b in self.answer_buttons:
            b.setEnabled(False)

        self.current_index += 1
        QTimer.singleShot(1200, self.show_question)  # Slightly longer delay to see colors


# ======================================================================
# GAMES: POKEMON (formerly games/pokemon_game.py)
# ======================================================================
class PokemonGame(BaseGame):
    def __init__(self):
        super().__init__()
        self.correct_name = ""
        self.score = 0
        self.rounds = 0
        self.max_rounds = 5
        self.current_pixmap = None  # Store the colored image here

        self.layout.addStretch()

        self.title_label = QLabel("Who's That Pokémon?")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #89b4fa; margin-bottom: 10px;")
        self.layout.addWidget(self.title_label, alignment=Qt.AlignCenter)

        # Image Display
        self.image_label = QLabel()
        self.image_label.setFixedSize(300, 300)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #313244; border-radius: 15px;")
        self.layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        self.status_label = QLabel("Score: 0")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 15px;")
        self.layout.addWidget(self.status_label, alignment=Qt.AlignCenter)

        # Answer Buttons (2x2 Grid)
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(10)
        self.answer_buttons = []

        for _ in range(4):
            btn = QPushButton()
            btn.setFixedSize(150, 50)
            btn.clicked.connect(self.check_answer)
            self.answer_buttons.append(btn)

        col1 = QVBoxLayout()
        col2 = QVBoxLayout()
        col1.addWidget(self.answer_buttons[0])
        col1.addWidget(self.answer_buttons[1])
        col2.addWidget(self.answer_buttons[2])
        col2.addWidget(self.answer_buttons[3])
        self.btn_layout.addLayout(col1)
        self.btn_layout.addLayout(col2)

        self.layout.addLayout(self.btn_layout)
        self.layout.addStretch()

        back_btn = QPushButton("← Back to Menu")
        back_btn.setFixedWidth(200)
        back_btn.clicked.connect(self.back_requested.emit)
        self.layout.addWidget(back_btn, alignment=Qt.AlignCenter)

    def start(self):
        self.score = 0
        self.rounds = 0
        self.next_round()

    def next_round(self):
        if self.rounds >= self.max_rounds:
            QMessageBox.information(self, "Game Over", f"Final Score: {self.score}/{self.max_rounds}")
            self.back_requested.emit()
            return

        self.status_label.setText(f"Score: {self.score} | Round {self.rounds + 1}/{self.max_rounds}")
        self.title_label.setText("Who's That Pokémon?")

        try:
            # Fetch Data
            self.correct_name, img_data = fetch_random_pokemon()
            wrong_names = fetch_random_names(3)
        except Exception as e:
            QMessageBox.critical(self, "API Error", str(e))
            self.back_requested.emit()
            return

        # Process Image
        pixmap = QPixmap()
        pixmap.loadFromData(img_data)
        pixmap = pixmap.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Save the colored image to memory
        self.current_pixmap = pixmap

        # Create Silhouette (Black out the image)
        silhouette = QPixmap(pixmap.size())
        silhouette.fill(Qt.transparent)
        painter = QPainter(silhouette)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(silhouette.rect(), QColor("#11111b"))  # Dark silhouette
        painter.end()

        self.image_label.setPixmap(silhouette)

        # Setup Buttons
        answers = [self.correct_name] + wrong_names
        random.shuffle(answers)

        for btn, ans in zip(self.answer_buttons, answers):
            btn.setText(ans)
            btn.setEnabled(True)
            btn.setStyleSheet("")  # Reset colors
            btn.setProperty("is_correct", ans == self.correct_name)

    def check_answer(self):
        btn = self.sender()
        is_correct = btn.property("is_correct")

        # Reveal the colored image
        if self.current_pixmap:
            self.image_label.setPixmap(self.current_pixmap)

        self.title_label.setText(f"It's {self.correct_name}!")

        if is_correct:
            self.score += 1
            btn.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold;")
        else:
            btn.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold;")
            # Highlight the correct button
            for b in self.answer_buttons:
                if b.property("is_correct"):
                    b.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold;")

        for b in self.answer_buttons:
            b.setEnabled(False)

        self.rounds += 1
        QTimer.singleShot(2500, self.next_round)  # 2.5 seconds so players can look at the revealed Pokémon


# ======================================================================
# GAMES: MEMORY MATCH (formerly games/memory_game.py)
# ======================================================================
class MemoryGame(BaseGame):
    def __init__(self):
        super().__init__()
        self.moves = 0
        self.pairs_found = 0
        self.first_card = None
        self.second_card = None
        self.is_checking = False

        self.layout.addStretch()

        self.title_label = QLabel("🦸 Cartoon Memory Match")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #89b4fa; margin-bottom: 10px;")
        self.layout.addWidget(self.title_label, alignment=Qt.AlignCenter)

        self.status_label = QLabel("Loading images...")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        self.layout.addWidget(self.status_label, alignment=Qt.AlignCenter)

        # The 4x4 Grid
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        self.layout.addWidget(self.grid_widget, alignment=Qt.AlignCenter)

        self.buttons = []
        self.default_style = """
            QPushButton {
                background-color: #313244;
                border: 2px solid #45475a;
                border-radius: 10px;
                font-size: 32px;
            }
            QPushButton:hover {
                border-color: #89b4fa;
            }
        """

        for row in range(4):
            for col in range(4):
                btn = QPushButton()
                btn.setFixedSize(100, 100)
                btn.setStyleSheet(self.default_style)
                btn.setText("❓")
                btn.clicked.connect(self.on_card_clicked)
                self.grid_layout.addWidget(btn, row, col)
                self.buttons.append(btn)

        self.layout.addStretch()

        back_btn = QPushButton("← Back to Menu")
        back_btn.setFixedWidth(200)
        back_btn.clicked.connect(self.back_requested.emit)
        self.layout.addWidget(back_btn, alignment=Qt.AlignCenter)

    def start(self):
        self.moves = 0
        self.pairs_found = 0
        self.first_card = None
        self.second_card = None
        self.is_checking = False

        # Reset buttons visually while loading
        for btn in self.buttons:
            btn.setText("❓")
            btn.setIcon(QIcon())
            btn.setStyleSheet(self.default_style)
            btn.setProperty("is_flipped", False)

        try:
            image_urls = fetch_cartoon_images(8)
            all_urls = image_urls + image_urls

            self.image_cache = {}
            for url in image_urls:
                # Using a User-Agent helps prevent image hosts from blocking the download
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                pixmap = QPixmap()
                pixmap.loadFromData(response.content)

                # Ensure the image actually loaded before caching it
                if not pixmap.isNull():
                    self.image_cache[url] = QIcon(
                        pixmap.scaled(90, 90, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                else:
                    raise ValueError("Image data was empty or corrupted.")

            random.shuffle(all_urls)

            for btn, url in zip(self.buttons, all_urls):
                btn.setProperty("image_url", url)
                btn.setProperty("is_flipped", False)
                btn.setText("❓")
                btn.setIcon(QIcon())
                btn.setStyleSheet(self.default_style)
                btn.setEnabled(True)

            self.update_status()

        except Exception as e:
            QMessageBox.critical(self, "API Error", f"Could not load cartoon images:\n{str(e)}")
            self.back_requested.emit()

    def update_status(self):
        self.status_label.setText(f"Moves: {self.moves} | Pairs Found: {self.pairs_found}/8")

    def on_card_clicked(self):
        if self.is_checking:
            return

        btn = self.sender()

        if btn.property("is_flipped"):
            return

        self.flip_card(btn, show_image=True)

        if not self.first_card:
            self.first_card = btn
        elif not self.second_card:
            self.second_card = btn
            self.moves += 1
            self.update_status()
            self.check_match()

    def flip_card(self, btn, show_image):
        if show_image:
            url = btn.property("image_url")
            btn.setIcon(self.image_cache[url])
            btn.setIconSize(QSize(90, 90))
            btn.setText("")
            btn.setProperty("is_flipped", True)
        else:
            btn.setIcon(QIcon())
            btn.setText("❓")
            btn.setProperty("is_flipped", False)
            btn.setStyleSheet(self.default_style)

    def check_match(self):
        self.is_checking = True
        url1 = self.first_card.property("image_url")
        url2 = self.second_card.property("image_url")

        if url1 == url2:
            match_style = """
                QPushButton {
                    background-color: #313244;
                    border: 3px solid #a6e3a1;
                    border-radius: 10px;
                }
            """
            self.first_card.setStyleSheet(match_style)
            self.second_card.setStyleSheet(match_style)

            self.pairs_found += 1
            self.update_status()
            self.reset_selection()
            self.check_win()
        else:
            QTimer.singleShot(1000, self.reset_flipped_cards)

    def reset_flipped_cards(self):
        self.flip_card(self.first_card, show_image=False)
        self.flip_card(self.second_card, show_image=False)
        self.reset_selection()

    def reset_selection(self):
        self.first_card = None
        self.second_card = None
        self.is_checking = False

    def check_win(self):
        if self.pairs_found == 8:
            QMessageBox.information(self, "You Win!", f"Congratulations!\nYou found all pairs in {self.moves} moves!")
            self.back_requested.emit()


# ======================================================================
# GAMES: GAME HUB (formerly ui/main_window.py -> MainWindow)
# Renamed to GameHubWindow to avoid clashing with the dashboard's MainWindow.
# ======================================================================
class GameHubWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Hub – PySide6 + APIs")
        self.resize(800, 650)
        self.setObjectName("mainWindow")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # ----- Menu screen -----
        self.menu_widget = QWidget()
        self.menu_widget.setObjectName("menuWidget")
        menu_layout = QVBoxLayout(self.menu_widget)
        menu_layout.setSpacing(14)

        # 1. Top stretch to push everything down
        menu_layout.addStretch()

        # Gaming Icon
        icon_label = QLabel("🎮")
        icon_label.setStyleSheet("font-size: 80px; margin-bottom: 10px;")
        menu_layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        title = QLabel("Choose a Game")
        title.setStyleSheet("font-size: 32px; font-weight: bold; margin-bottom: 30px; color: #89b4fa;")
        menu_layout.addWidget(title, alignment=Qt.AlignCenter)

        games = [
            ("🎯 Trivia Quiz", TriviaGame),
            ("⚡ Who's That Pokémon?", PokemonGame),
            ("🦸 Memory Match", MemoryGame),
        ]

        menu_button_style = """
            QPushButton {
                background-color: #181818;
                color: #e0e0e0;
                border: 2px solid #45475a;
                border-radius: 10px;
                padding: 12px 18px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1e1e2e;
                color: #89b4fa;
                border: 2px solid #89b4fa;
            }
        """

        for name, game_class in games:
            btn = QPushButton(name)
            btn.setObjectName("menuButton")
            btn.setFixedSize(350, 56)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(menu_button_style)
            btn.clicked.connect(lambda checked, gc=game_class: self.launch_game(gc))
            menu_layout.addWidget(btn, alignment=Qt.AlignCenter)

        # 2. Bottom stretch to push everything up
        menu_layout.addStretch()

        self.stack.addWidget(self.menu_widget)

    def launch_game(self, game_class):
        game = game_class()
        game.back_requested.connect(self.show_menu)
        self.stack.addWidget(game)
        self.stack.setCurrentWidget(game)
        game.start()

    def show_menu(self):
        current = self.stack.currentWidget()
        if current is not self.menu_widget:
            self.stack.removeWidget(current)
            current.deleteLater()
        self.stack.setCurrentWidget(self.menu_widget)


# ======================================================================
# VIDEO (Video tab)
# ======================================================================
VIDEO_STYLE = """
QWidget {
    background-color: #080B14;
    color: #FFFFFF;
    font-family: 'Segoe UI', -apple-system, sans-serif;
}
QLineEdit {
    background-color: #151A28;
    border: 1px solid #252B3D;
    border-radius: 20px;
    padding: 8px 15px;
    color: white;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #3B82F6;
    background-color: #1A2033;
}
QPushButton#NavBtn {
    background-color: transparent;
    border: none;
    border-radius: 16px;
    padding: 8px 16px;
    color: #9CA3AF;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#NavBtn:hover { color: #FFFFFF; }
QPushButton#NavBtnActive {
    background-color: #FFFFFF;
    border: none;
    border-radius: 16px;
    padding: 8px 16px;
    color: #080B14;
    font-weight: 700;
    font-size: 13px;
}
#HeroFrame {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #080B14, stop:0.3 #101D35, stop:0.6 #2A1B30, stop:1 #080B14);
    border-radius: 16px;
    border: 1px solid #1F2937;
}
QLabel#HeroTitle {
    background: transparent;
    font-size: 38px;
    font-weight: 900;
    color: white;
}
QLabel#HeroDesc {
    background: transparent;
    font-size: 15px;
    color: #D1D5DB;
}
QLabel#TagLabel {
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    color: #E5E7EB;
}
QPushButton#PlayBtn {
    background-color: #0056D2;
    border-radius: 22px;
    border: none;
    color: white;
    font-size: 18px;
    font-weight: bold;
}
QPushButton#PlayBtn:hover { background-color: #2563EB; }
QPushButton#SeeMoreBtn {
    background-color: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 24px;
    color: white;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#SeeMoreBtn:hover { background-color: rgba(255, 255, 255, 0.2); }
QScrollArea { border: none; background: transparent; }
QScrollBar:horizontal { height: 0px; background: transparent; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: #252B3D; border-radius: 4px; min-height: 20px; }
QPushButton#LogoBtn {
    background: transparent;
    border: none;
    font-size: 22px;
    font-weight: 900;
    color: white;
    text-align: left;
    padding: 0;
}
QLabel#ShelfIcon { font-size: 18px; color: #3B82F6; background: transparent; }
QLabel#ShelfTitle { font-size: 20px; font-weight: 700; color: white; background: transparent; }
QLabel#ViewAllLink { font-size: 12px; color: #3B82F6; background: transparent; }
QPushButton#ArrowBtn {
    background-color: #151A28;
    border: 1px solid #252B3D;
    border-radius: 16px;
    color: #A0AAB5;
    font-size: 18px;
    font-weight: 700;
}
QPushButton#ArrowBtn:hover { background-color: #1F2937; color: white; border-color: #3B82F6; }
QLabel#RatingBadge {
    background-color: rgba(13, 17, 23, 0.92);
    border: 2px solid #10B981;
    border-radius: 17px;
    color: white;
    font-size: 11px;
    font-weight: 700;
}
QLabel#PosterRibbon {
    background-color: #0056D2;
    color: white;
    font-size: 10px;
    font-weight: 600;
    border-bottom-left-radius: 10px;
    border-bottom-right-radius: 10px;
}
QFrame#FilterSidebar {
    background-color: #0D1117;
    border: 1px solid #1F2937;
    border-radius: 14px;
    margin-right: 20px;
}
QLabel#FilterHeading { font-size: 16px; font-weight: 800; color: white; background: transparent; }
QLabel#FilterLabel { font-size: 13px; font-weight: 600; color: #D1D5DB; background: transparent; }
QLabel#MutedLabel { color: #9CA3AF; font-size: 12px; background: transparent; }
QComboBox {
    background-color: #151A28;
    border: 1px solid #252B3D;
    border-radius: 10px;
    padding: 6px 12px;
    color: white;
    font-size: 13px;
}
QComboBox:hover { border-color: #3B82F6; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background-color: #151A28;
    color: white;
    border: 1px solid #252B3D;
    selection-background-color: #0056D2;
    outline: 0;
}
QPushButton#IconBtn {
    background-color: #151A28;
    border: 1px solid #252B3D;
    border-radius: 10px;
    color: #A0AAB5;
    font-size: 16px;
}
QPushButton#IconBtn:hover { border-color: #3B82F6; color: white; }
"""

_VIDEO_NAM = None


def _video_nam():
    global _VIDEO_NAM
    if _VIDEO_NAM is None:
        _VIDEO_NAM = QNetworkAccessManager()
    return _VIDEO_NAM


class RemoteImage(QObject):
    loaded = Signal(QPixmap)
    failed = Signal()
    _cache = {}

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.reply = None

        if not url:
            QTimer.singleShot(0, self.failed.emit)
            return
        if url in RemoteImage._cache:
            pix = RemoteImage._cache[url]
            QTimer.singleShot(0, lambda: self.loaded.emit(pix))
            return

        request = QNetworkRequest(QUrl(url))
        request.setHeader(
            QNetworkRequest.UserAgentHeader,
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        self.reply = _video_nam().get(request)
        self.reply.finished.connect(self._on_done)

    def _on_done(self):
        reply = self.reply
        self.reply = None
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                pix = QPixmap()
                pix.loadFromData(reply.readAll())
                if not pix.isNull():
                    RemoteImage._cache[self.url] = pix
                    self.loaded.emit(pix)
                    return
            self.failed.emit()
        finally:
            reply.deleteLater()


class PosterImage(QWidget):
    def __init__(self, radius: int = 10, parent=None):
        super().__init__(parent)
        self._pix = None
        self._radius = radius
        self._hovered = False

    def set_pixmap(self, pix: QPixmap):
        self._pix = pix
        self.update()

    def set_hovered(self, hovered: bool):
        self._hovered = hovered
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self._radius, self._radius)
        painter.setClipPath(path)

        if self._pix and not self._pix.isNull():
            scaled = self._pix.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(-x, -y, scaled)
        else:
            painter.fillRect(self.rect(), QColor("#1F2937"))

        painter.setClipping(False)
        pen = QPen(QColor("#FFFFFF") if self._hovered else QColor("#1F2937"))
        pen.setWidth(2 if self._hovered else 1)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), self._radius, self._radius)
        painter.end()


class RatingBadge(QLabel):
    def __init__(self, rating: float, parent=None):
        super().__init__(f"{rating:.1f}", parent)
        self.setObjectName("RatingBadge")
        self.setFixedSize(34, 34)
        self.setAlignment(Qt.AlignCenter)


class PosterCard(QWidget):
    card_clicked = Signal(dict)

    def __init__(self, video_data: dict, width: int = 240, radius: int = 10, parent=None):
        super().__init__(parent)
        self.video_data = video_data
        self.image_url = video_data.get("image_url")
        self.rating = video_data.get("rating")
        self.ribbon = video_data.get("ribbon")

        height = int(width * 9 / 16)
        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)

        self.poster = PosterImage(radius=radius, parent=self)
        self.poster.setGeometry(0, 0, width, height)

        if self.image_url:
            loader = RemoteImage(self.image_url, self)
            loader.loaded.connect(self.poster.set_pixmap)

        if self.rating is not None:
            badge = RatingBadge(self.rating, parent=self)
            badge.move(8, 8)

        if self.ribbon:
            rib = QLabel(self.ribbon, self)
            rib.setObjectName("PosterRibbon")
            rib.setAlignment(Qt.AlignCenter)
            rib.setFixedHeight(22)
            rib.setGeometry(0, height - 22, width, 22)

    def enterEvent(self, event):
        self.poster.set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.poster.set_hovered(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self.video_data)
        super().mousePressEvent(event)


class VideoShelf(QWidget):
    view_all_clicked = Signal()
    card_clicked = Signal(dict)

    def __init__(self, title: str, icon: str = "", cards=None, card_width: int = 240, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(10)
        if icon:
            ic = QLabel(icon)
            ic.setObjectName("ShelfIcon")
            head.addWidget(ic)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("ShelfTitle")
        head.addWidget(title_lbl)

        view_all = QLabel("View all")
        view_all.setObjectName("ViewAllLink")
        view_all.setCursor(Qt.PointingHandCursor)
        view_all.mousePressEvent = lambda event: self.view_all_clicked.emit()
        head.addWidget(view_all)
        head.addStretch()

        self.prev_btn = QPushButton("‹")
        self.next_btn = QPushButton("›")
        for btn in (self.prev_btn, self.next_btn):
            btn.setObjectName("ArrowBtn")
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.PointingHandCursor)
        self.prev_btn.clicked.connect(lambda: self._scroll(-200))
        self.next_btn.clicked.connect(lambda: self._scroll(200))
        head.addWidget(self.prev_btn)
        head.addWidget(self.next_btn)
        root.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFixedHeight(int(card_width * 9 / 16) + 8)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        row_host = QWidget()
        row_host.setStyleSheet("background: transparent;")
        row = QHBoxLayout(row_host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.setAlignment(Qt.AlignLeft)
        for data in cards or []:
            card = PosterCard(data, width=card_width)
            card.card_clicked.connect(self.card_clicked)
            row.addWidget(card)
        row.addStretch()
        self.scroll.setWidget(row_host)
        root.addWidget(self.scroll)

    def _scroll(self, dx):
        bar = self.scroll.horizontalScrollBar()
        bar.setValue(bar.value() + dx)


class VideoFilterSidebar(QFrame):
    filters_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FilterSidebar")
        self.setFixedWidth(290)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(4)

        heading = QLabel("Filters")
        heading.setObjectName("FilterHeading")
        root.addWidget(heading)

        label = QLabel("Duration")
        label.setObjectName("FilterLabel")
        root.addWidget(label)
        self.duration = QComboBox()
        self.duration.addItems(["Any length", "Under 5 mins", "5-15 mins", "Over 15 mins"])
        self.duration.setMinimumHeight(38)
        self.duration.currentTextChanged.connect(self._emit_filters)
        root.addWidget(self.duration)
        root.addStretch()

    def _emit_filters(self):
        self.filters_changed.emit({"duration": self.duration.currentText()})


class TrendingPage(QWidget):
    card_clicked = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = VideoFilterSidebar()
        self.sidebar.filters_changed.connect(self.apply_filters)
        root.addWidget(self.sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(20, 10, 20, 20)
        right_layout.setSpacing(14)

        toolbar = QHBoxLayout()
        filter_btn = QPushButton("⫶")
        filter_btn.setObjectName("IconBtn")
        filter_btn.setFixedSize(38, 38)
        toolbar.addWidget(filter_btn)
        toolbar.addStretch()
        self.showing = QLabel("Showing 0 Videos")
        self.showing.setObjectName("MutedLabel")
        toolbar.addWidget(self.showing)
        self.sort_by = QComboBox()
        self.sort_by.addItems(["Default", "Title (A-Z)", "Title (Z-A)"])
        self.sort_by.setFixedWidth(140)
        self.sort_by.currentTextChanged.connect(self.apply_filters)
        toolbar.addWidget(self.sort_by)
        right_layout.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.grid_host = QWidget()
        self.grid_host.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(16)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll.setWidget(self.grid_host)
        right_layout.addWidget(self.scroll, 1)
        root.addWidget(right, 1)

        self._original_data = []
        self._current_cols = 3
        self._current_width = 280

    def set_cards(self, cards_data: list, cols: int = 3, card_width: int = 280):
        self._original_data = list(cards_data or [])
        self._current_cols = cols
        self._current_width = card_width
        self.apply_filters()

    def apply_filters(self):
        duration_filter = self.sidebar.duration.currentText()
        filtered = []
        for video in self._original_data:
            secs = video.get("duration", 0) or 0
            if duration_filter != "Any length":
                if secs == 0:
                    continue
                if duration_filter == "Under 5 mins" and secs >= 300:
                    continue
                if duration_filter == "5-15 mins" and (secs < 300 or secs > 900):
                    continue
                if duration_filter == "Over 15 mins" and secs <= 900:
                    continue
            filtered.append(video)

        sort_mode = self.sort_by.currentText()
        if sort_mode == "Title (A-Z)":
            filtered.sort(key=lambda item: item.get("title", "").lower())
        elif sort_mode == "Title (Z-A)":
            filtered.sort(key=lambda item: item.get("title", "").lower(), reverse=True)

        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, data in enumerate(filtered):
            card = PosterCard(data, width=self._current_width)
            card.card_clicked.connect(self.card_clicked)
            row, col = divmod(index, self._current_cols)
            self.grid.addWidget(card, row, col)
        self.showing.setText(f"Showing {len(filtered)} Videos")


class VideoHeroBanner(QFrame):
    def __init__(self, video_data: dict, show_details_cb, parent=None):
        super().__init__(parent)
        self.setObjectName("HeroFrame")
        self.setMinimumHeight(400)

        self.bg_label = QLabel(self)
        self.bg_label.setScaledContents(True)
        self.overlay = QLabel(self)
        self.overlay.setStyleSheet("background-color: rgba(8, 11, 20, 0.7); border-radius: 16px;")

        hero_layout = QVBoxLayout(self)
        hero_layout.setContentsMargins(50, 50, 50, 30)
        hero_layout.addStretch()

        title = QLabel(video_data.get("title", "Loading Videos...").upper())
        title.setObjectName("HeroTitle")
        title.setWordWrap(True)
        hero_layout.addWidget(title)

        tags = QHBoxLayout()
        duration = QLabel("00:00")
        duration.setObjectName("TagLabel")
        genre = QLabel(video_data.get("genre", "Please wait"))
        genre.setObjectName("TagLabel")
        tags.addWidget(duration)
        tags.addWidget(genre)
        tags.addStretch()
        hero_layout.addLayout(tags)

        desc = QLabel(video_data.get(
            "desc",
            "Fetching the latest and trending movies from the API. This will only take a moment.",
        ))
        desc.setObjectName("HeroDesc")
        desc.setWordWrap(True)
        hero_layout.addWidget(desc)
        hero_layout.addSpacing(20)

        bottom = QHBoxLayout()
        play_btn = QPushButton("▶")
        play_btn.setObjectName("PlayBtn")
        play_btn.setFixedSize(44, 44)
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.clicked.connect(lambda: show_details_cb(video_data))
        details_btn = QPushButton("ⓘ  Details")
        details_btn.setObjectName("SeeMoreBtn")
        details_btn.setFixedHeight(44)
        details_btn.setFixedWidth(140)
        details_btn.setCursor(Qt.PointingHandCursor)
        details_btn.clicked.connect(lambda: show_details_cb(video_data))
        bottom.addWidget(play_btn)
        bottom.addSpacing(10)
        bottom.addWidget(details_btn)
        bottom.addStretch()
        hero_layout.addLayout(bottom)

        if video_data and video_data.get("image_url"):
            loader = RemoteImage(video_data["image_url"], self)
            loader.loaded.connect(self._set_bg)

    def _set_bg(self, pix: QPixmap):
        self.bg_label.setPixmap(pix)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bg_label.setGeometry(0, 0, self.width(), self.height())
        self.overlay.setGeometry(0, 0, self.width(), self.height())


class VideoDetailsPage(QWidget):
    def __init__(self, play_video_cb, go_back_cb, parent=None):
        super().__init__(parent)
        self.play_video_cb = play_video_cb
        self.current_video = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 20, 40, 40)
        layout.setSpacing(20)

        top_bar = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("NavBtn")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(go_back_cb)
        top_bar.addWidget(back_btn)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        content = QHBoxLayout()
        content.setSpacing(40)
        self.poster_label = QLabel()
        self.poster_label.setFixedSize(640, 360)
        self.poster_label.setStyleSheet("background-color: #1F2937; border-radius: 12px;")
        content.addWidget(self.poster_label)

        info = QVBoxLayout()
        info.setSpacing(15)
        self.title_lbl = QLabel("Video Title")
        self.title_lbl.setStyleSheet("font-size: 36px; font-weight: 900; color: white; background: transparent;")
        self.title_lbl.setWordWrap(True)
        self.genre_lbl = QLabel("Category")
        self.genre_lbl.setStyleSheet("font-size: 16px; color: #A0AAB5; font-weight: bold; background: transparent;")
        self.rating_lbl = QLabel("⭐ 0.0")
        self.rating_lbl.setStyleSheet("font-size: 18px; color: #10B981; font-weight: bold; background: transparent;")
        self.desc_lbl = QLabel("Description...")
        self.desc_lbl.setStyleSheet("font-size: 16px; color: #D1D5DB; background: transparent;")
        self.desc_lbl.setWordWrap(True)
        info.addWidget(self.title_lbl)
        info.addWidget(self.genre_lbl)
        info.addWidget(self.rating_lbl)
        info.addSpacing(10)
        info.addWidget(self.desc_lbl)
        info.addStretch()

        self.play_btn = QPushButton("▶  Play Video")
        self.play_btn.setFixedSize(200, 50)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setStyleSheet(
            "QPushButton { background-color: #0056D2; color: white; border-radius: 25px; "
            "font-size: 18px; font-weight: bold; border: none; }"
            "QPushButton:hover { background-color: #2563EB; }"
        )
        self.play_btn.clicked.connect(self._on_play)
        info.addWidget(self.play_btn)
        content.addLayout(info, 1)
        layout.addLayout(content)
        layout.addStretch()

    def load_video(self, video_data: dict):
        self.current_video = video_data
        self.title_lbl.setText(video_data.get("title", "Unknown Title"))
        self.genre_lbl.setText(video_data.get("genre", "Uncategorized"))
        rating = video_data.get("rating")
        if rating is not None:
            self.rating_lbl.setText(f"⭐ {rating}")
            self.rating_lbl.show()
        else:
            self.rating_lbl.hide()
        self.desc_lbl.setText(video_data.get("desc", "No description available for this video."))
        url = video_data.get("image_url")
        if url:
            loader = RemoteImage(url, self)
            loader.loaded.connect(self._set_poster)

    def _set_poster(self, pix):
        self.poster_label.setPixmap(
            pix.scaled(640, 360, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        )

    def _on_play(self):
        source = self.current_video.get("source")
        if source:
            self.play_video_cb(source, self.current_video.get("title", "Video"))


class VideoHomePage(QWidget):
    def __init__(self, latest_videos, trending_videos, show_details_cb, view_all_cb, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(24)

        hero_video = latest_videos[0] if latest_videos else {}
        layout.addWidget(VideoHeroBanner(hero_video, show_details_cb))

        latest = VideoShelf("Latest Uploads", icon="🆕", cards=latest_videos[:10], card_width=260)
        latest.card_clicked.connect(show_details_cb)
        latest.view_all_clicked.connect(lambda videos=list(latest_videos): view_all_cb(videos, "Latest Uploads"))
        layout.addWidget(latest)

        trending = VideoShelf("Trending Now", icon="🔥", cards=trending_videos[:10], card_width=260)
        trending.card_clicked.connect(show_details_cb)
        trending.view_all_clicked.connect(lambda videos=list(trending_videos): view_all_cb(videos, "Trending Now"))
        layout.addWidget(trending)
        layout.addStretch()
        scroll.setWidget(content)


class VideoPlayerDialog(QDialog):
    def __init__(self, url: str, title: str = "Now Playing", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1280, 720)
        self.setStyleSheet("background-color: #080B14;")
        self._pause_dashboard_music()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.video = QVideoWidget()
        self.video.setStyleSheet("background-color: black;")
        root.addWidget(self.video, 1)

        bar = QWidget()
        bar.setFixedHeight(64)
        bar.setStyleSheet("background-color: #0D1117;")
        controls = QHBoxLayout(bar)
        controls.setContentsMargins(15, 8, 15, 8)
        controls.setSpacing(12)

        skip_style = (
            "QPushButton { background:#1F2937; color:white; border-radius:8px; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#374151; }"
        )
        self.skip_back_btn = QPushButton("⏪ 10s")
        self.skip_back_btn.setFixedSize(60, 42)
        self.skip_back_btn.setStyleSheet(skip_style)
        self.skip_back_btn.clicked.connect(lambda: self._skip(-10000))

        self.play_btn = QPushButton("⏸")
        self.play_btn.setFixedSize(42, 42)
        self.play_btn.setStyleSheet(
            "QPushButton { background:#0056D2; color:white; border-radius:21px; font-size:18px; font-weight:bold; }"
            "QPushButton:hover { background:#2563EB; }"
        )
        self.play_btn.clicked.connect(self._toggle_play)

        self.skip_fwd_btn = QPushButton("10s ⏩")
        self.skip_fwd_btn.setFixedSize(60, 42)
        self.skip_fwd_btn.setStyleSheet(skip_style)
        self.skip_fwd_btn.clicked.connect(lambda: self._skip(10000))

        self.seek = QSlider(Qt.Horizontal)
        self.seek.sliderMoved.connect(self._on_seek)
        self.seek.sliderPressed.connect(self._on_seek_start)
        self.seek.sliderReleased.connect(self._on_seek_end)

        self.time_lbl = QLabel("0:00 / 0:00")
        self.time_lbl.setStyleSheet("color:#E5E7EB; font-size:12px; background: transparent;")

        self.audio = QAudioOutput()
        self.audio.setVolume(1.0)
        self.vol = QSlider(Qt.Horizontal)
        self.vol.setFixedWidth(110)
        self.vol.setRange(0, 100)
        self.vol.setValue(100)
        self.vol.valueChanged.connect(lambda value: self.audio.setVolume(value / 100.0))

        controls.addWidget(self.skip_back_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.skip_fwd_btn)
        controls.addWidget(self.seek, 1)
        controls.addWidget(self.time_lbl)
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("background: transparent; color: white;")
        controls.addWidget(vol_icon)
        controls.addWidget(self.vol)
        root.addWidget(bar)

        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(self._on_dur)
        self.player.playbackStateChanged.connect(self._on_state)
        self.player.errorOccurred.connect(self._on_err)
        self.player.setSource(QUrl(url))
        self.player.play()

    def _pause_dashboard_music(self):
        widget = self.parent()
        while widget is not None:
            player = getattr(widget, "media_player", None)
            if player is not None and player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                player.pause()
                return
            widget = widget.parent()

    def _skip(self, ms: int):
        self.player.setPosition(max(0, self.player.position() + ms))

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _on_seek_start(self):
        self._was_playing = self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self.player.pause()

    def _on_seek(self, pos):
        self.player.setPosition(pos)

    def _on_seek_end(self):
        if getattr(self, "_was_playing", False):
            self.player.play()

    def _on_pos(self, pos):
        if not self.seek.isSliderDown():
            self.seek.setValue(pos)
        self.time_lbl.setText(f"{self._fmt(pos)} / {self._fmt(self.player.duration())}")

    def _on_dur(self, dur):
        self.seek.setRange(0, max(0, dur))
        self.time_lbl.setText(f"{self._fmt(0)} / {self._fmt(dur)}")

    def _on_state(self, state):
        self.play_btn.setText("⏸" if state == QMediaPlayer.PlaybackState.PlayingState else "▶")

    def _on_err(self, err, msg):
        print(f"[player] {err}: {msg}")
        self.time_lbl.setText("playback error")

    @staticmethod
    def _fmt(ms: int) -> str:
        seconds = max(0, int(ms // 1000))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"

    def closeEvent(self, event):
        self.player.stop()
        super().closeEvent(event)


class VideoHub(QWidget):
    """Movie browser embedded in the dashboard Video tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoHub")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(VIDEO_STYLE)

        self.latest_videos = []
        self.trending_videos = []
        self._latest_ready = False
        self._trending_ready = False

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 15, 20, 20)
        root.setSpacing(15)

        nav = QHBoxLayout()
        logo = QPushButton("▶  Videos")
        logo.setObjectName("LogoBtn")
        logo.setCursor(Qt.PointingHandCursor)
        nav.addWidget(logo)
        nav.addStretch()

        self.welcome_label = QLabel("Welcome, User!")
        self.welcome_label.setStyleSheet(
            "color: #0055ff; font-size: 14px; font-weight: bold; background: transparent;"
        )
        nav.addWidget(self.welcome_label)

        self.btn_home = QPushButton("Home")
        self.btn_trending = QPushButton("🔥 Trending Video")
        for btn in (self.btn_home, self.btn_trending):
            btn.setObjectName("NavBtn")
            btn.setCursor(Qt.PointingHandCursor)
            nav.addWidget(btn)
        root.addLayout(nav)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.home_page = VideoHomePage(self.latest_videos, self.trending_videos, self._show_details, self._view_all)
        self.trending_page = TrendingPage()
        self.trending_page.card_clicked.connect(self._show_details)
        self.details_page = VideoDetailsPage(self._play_video, self._go_back)
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.trending_page)
        self.stack.addWidget(self.details_page)

        logo.clicked.connect(lambda: self._switch(0))
        self.btn_home.clicked.connect(lambda: self._switch(0))
        self.btn_trending.clicked.connect(lambda: self._switch(1))
        self._switch(0)

        self.pixabay_client = PixabayVideoClient("58841597-5e23bdcee5aa3ed60c1ed9cec", self)
        self.pixabay_client.results_ready.connect(self._on_search_results)
        self.pixabay_client.search_failed.connect(self._on_search_failed)

        self.archive_latest = VideoSearchClient(self)
        self.archive_latest.results_ready.connect(self._on_latest_loaded)
        self.archive_latest.search_failed.connect(lambda msg: self._on_api_failed("latest"))
        self.archive_latest.fetch_latest(limit=12)

        self.archive_trending = VideoSearchClient(self)
        self.archive_trending.results_ready.connect(self._on_trending_loaded)
        self.archive_trending.search_failed.connect(lambda msg: self._on_api_failed("trending"))
        self.archive_trending.fetch_trending(limit=12)

    def _on_latest_loaded(self, videos):
        self.latest_videos = videos
        self._latest_ready = True
        self._check_home_ready()

    def _on_trending_loaded(self, videos):
        self.trending_videos = videos
        self._trending_ready = True
        self._check_home_ready()

    def _on_api_failed(self, which):
        if which == "latest":
            self._latest_ready = True
        else:
            self._trending_ready = True
        self._check_home_ready()

    def _check_home_ready(self):
        if not (self._latest_ready and self._trending_ready):
            return
        self.stack.removeWidget(self.home_page)
        self.home_page.deleteLater()
        self.home_page = VideoHomePage(
            self.latest_videos, self.trending_videos, self._show_details, self._view_all
        )
        self.stack.insertWidget(0, self.home_page)
        self.trending_page.set_cards(self.latest_videos + self.trending_videos, cols=3, card_width=280)
        self._switch(0)

    def _view_all(self, videos, title):
        self.trending_page.set_cards(videos, cols=3, card_width=280)
        self._switch(1)

    def _switch(self, index: int):
        self.stack.setCurrentIndex(index)
        for btn in (self.btn_home, self.btn_trending):
            btn.setObjectName("NavBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        active = self.btn_home if index == 0 else self.btn_trending
        active.setObjectName("NavBtnActive")
        active.style().unpolish(active)
        active.style().polish(active)

    def _show_details(self, video_data: dict):
        if not video_data:
            return
        self.details_page.load_video(video_data)
        self.stack.setCurrentWidget(self.details_page)

    def _go_back(self):
        self._switch(0)

    def _play_video(self, url: str, title: str = "Now Playing"):
        VideoPlayerDialog(url, title, self).exec()

    def _on_search(self, query):
        query = (query or "").strip()
        if not query:
            return
        self.pixabay_client.search(query, limit=20)

    def _on_search_results(self, videos: list):
        if not videos:
            self._on_search_failed("No related videos found.")
            return
        self.trending_page.set_cards(videos, cols=3, card_width=280)
        self._switch(1)

    def _on_search_failed(self, message: str):
        previous = self.welcome_label.text()
        self.welcome_label.setText(message)
        QTimer.singleShot(3000, lambda: self.welcome_label.setText(previous))


# ======================================================================
# DASHBOARD
# ======================================================================
class ClickableFrame(QFrame):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SearchWorker(QThread):
    finished_search = Signal(int, str, dict, dict)
    def __init__(self, request_id, query):
        super().__init__()
        self.request_id = request_id
        self.query = query
    def run(self):
        results = jamendo_api.search_catalog(
            self.query, artist_limit=6, artist_tracks_limit=6, track_limit=20,
        )
        urls = set()
        for artist in results.get("artists", []):
            if artist.get("image"): urls.add(artist["image"])
            for t in artist.get("tracks", []):
                img = t.get("album_image") or t.get("image")
                if img: urls.add(img)
        for t in results.get("tracks", []):
            img = t.get("album_image") or t.get("image")
            if img: urls.add(img)
        image_bytes = {}
        url_list = list(urls)
        if url_list:
            with ThreadPoolExecutor(max_workers=8) as pool:
                fetched = list(pool.map(jamendo_api.download_image_bytes, url_list))
            for url, raw in zip(url_list, fetched):
                if raw: image_bytes[url] = raw
        self.finished_search.emit(self.request_id, self.query, results, image_bytes)


class MainWindow(QMainWindow):
    logout_requested = Signal()

    def __init__(self, username="User"):
        super().__init__()
        self.username = username
        
        self.setWindowTitle("Pulse")
        self.resize(1100, 800)
        self.setStyleSheet(DARK_THEME)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        self.current_audio_url = ""
        self.current_track = None
        self.current_playlist = []
        self.current_index = -1
        self._expected_duration_ms = 0
        self._seeking = False
        self._last_volume = 80
        self.current_music_page = 0

        self.home_play_buttons = []
        self.search_play_buttons = []
        self.library_play_buttons = []
        self.home_duration_labels = []
        self.search_duration_labels = []
        self.library_duration_labels = []
        self.home_heart_buttons = []
        self.search_heart_buttons = []
        self.library_heart_buttons = []

        self._pixmap_cache = {}
        self._search_request_id = 0
        self._active_workers = set()
        self.search_filter = "ALL"
        self.last_search_results = None
        self.search_history = []
        self.recently_played = []
        self.liked_tracks = []
        self.library_filter = "All"

        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(350)
        self.search_debounce_timer.timeout.connect(lambda: self.run_search(self.big_search.text()))

        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.audio_output.setVolume(0.8)

        main_widget = QWidget()
        main_widget.setObjectName("MainContainer")
        self.setCentralWidget(main_widget)
        
        outer_layout = QVBoxLayout(main_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # TOP HEADER
        header = QWidget()
        header.setObjectName("TopHeader")
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(30, 0, 30, 0)

        logo_box = QHBoxLayout()
        logo_icon = QLabel("▶")
        logo_icon.setStyleSheet("background: #0055ff; color: white; border-radius: 4px; padding: 2px 6px; font-size: 12px;")
        logo_text = QLabel("Pulse")
        logo_text.setStyleSheet("color: white; font-weight: bold; font-size: 16px; margin-left: 5px;")
        logo_box.addWidget(logo_icon)
        logo_box.addWidget(logo_text)

        seg_widget = QWidget()
        seg_widget.setObjectName("SegmentedControl")
        seg_widget.setFixedSize(240, 34)
        seg_layout = QHBoxLayout(seg_widget)
        seg_layout.setContentsMargins(4, 4, 4, 4)
        seg_layout.setSpacing(0)

        self.mode_buttons = []
        for i, text in enumerate(["Music", "Video", "Games"]):
            btn = QPushButton(text)
            btn.setObjectName("SegBtnActive" if i == 0 else "SegBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedWidth(77)
            btn.clicked.connect(lambda checked, idx=i: self._set_top_mode(idx))
            seg_layout.addWidget(btn)
            self.mode_buttons.append(btn)

        self.header_search = QLineEdit()
        self.header_search.setObjectName("SearchBar")
        self.header_search.setPlaceholderText("🔍 Search artists or songs...")
        self.header_search.setFixedSize(240, 30)
        self.header_search.returnPressed.connect(self._on_header_search)

        self.profile_label = QPushButton("U")
        self.profile_label.setFixedSize(30, 30)
        self.profile_label.setCursor(Qt.PointingHandCursor)
        self.profile_label.setToolTip("Account")
        self.profile_label.setStyleSheet(
            "QPushButton { background: white; color: black; border: none; border-radius: 15px; "
            "font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background: #d6e4ff; }"
        )
        self.profile_label.clicked.connect(self._open_profile_menu)

        h_layout.addLayout(logo_box)
        h_layout.addStretch()
        h_layout.addWidget(seg_widget)
        h_layout.addStretch()
        h_layout.addWidget(self.header_search)
        h_layout.addWidget(self.profile_label)

        # NAVBAR
        self.navbar = QWidget()
        self.navbar.setObjectName("TopNavBar")
        self.navbar.setFixedHeight(56)
        nav_layout = QHBoxLayout(self.navbar)
        nav_layout.setContentsMargins(30, 0, 30, 0)
        nav_layout.setSpacing(8)

        self.nav_buttons = []
        nav_items = [("Home", 0), ("Search", 1), ("Your Library", 2)]
        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=index: self.set_page(i))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        self._update_nav_pills(0)
        nav_layout.addStretch()

        # STACKED WIDGET
        self.stacked_widget = QStackedWidget()
        
        self.stacked_widget.addWidget(self.build_home_page())      # Index 0
        self.stacked_widget.addWidget(self.build_search_page())    # Index 1
        self.stacked_widget.addWidget(self.build_library_page())   # Index 2
        self.stacked_widget.addWidget(self.build_video_page())     # Index 3
        self.stacked_widget.addWidget(self.build_games_page())     # Index 4 (Games)

        # --- ASSEMBLE LAYOUT ---
        outer_layout.addWidget(header)
        outer_layout.addWidget(self.navbar)
        
        # Stretch factor 1 ensures the content expands but doesn't push the player bar off
        self.stacked_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        outer_layout.addWidget(self.stacked_widget, 1)
        
        self.player_bar = self.create_player_bar()
        outer_layout.addWidget(self.player_bar)

        # Update username after all UI elements are built
        self.set_username(self.username)

    def build_games_page(self):
        """Embeds the Game Hub (defined above in this file) while preventing window resizing."""
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        # Instantiate the Game Hub
        self.game_hub = GameHubWindow()
        self.game_hub.setWindowFlags(Qt.Widget) 
        
        # Force the Game Hub to ignore its minimum size so it fits in the scroll area
        self.game_hub.setMinimumSize(0, 0)
        self.game_hub.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        
        # Add a back button visually inside the Game Hub layout
        back_btn = QPushButton("← Back to Music Dashboard")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(
            "background-color: #313244; color: #cdd6f4; border: 2px solid #45475a; "
            "border-radius: 8px; padding: 10px 20px; font-weight: bold; font-size: 14px;"
        )
        back_btn.clicked.connect(lambda: self._set_top_mode(0))
        
        # Insert the back button into the menu layout at index 0
        self.game_hub.menu_widget.layout().insertWidget(0, back_btn, alignment=Qt.AlignLeft)

        scroll.setWidget(self.game_hub)
        layout.addWidget(scroll)
        return wrapper

    def set_username(self, username):
        self.username = username
        initial = self.username[0].upper() if self.username else "U"
        self.profile_label.setText(initial)
        if hasattr(self, 'home_welcome_label'):
            self.home_welcome_label.setText(f"Welcome back, {self.username}!")
        if hasattr(self, 'video_welcome_label'):
            self.video_welcome_label.setText(f"Welcome, {self.username}!")

    def _set_top_mode(self, mode_index):
        for i, btn in enumerate(self.mode_buttons):
            btn.setObjectName("SegBtnActive" if i == mode_index else "SegBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        if mode_index == 0:
            self.navbar.show()
            self.player_bar.show()
            self.header_search.setPlaceholderText("🔍 Search artists or songs...")
            self.stacked_widget.setCurrentIndex(self.current_music_page)
        elif mode_index == 1:
            self.navbar.hide()
            self.player_bar.hide()
            self.header_search.setPlaceholderText("🔍 Search videos...")
            self.stacked_widget.setCurrentIndex(3)
        elif mode_index == 2:
            self.navbar.hide()
            self.player_bar.hide()
            self.header_search.setPlaceholderText("🔍 Search artists or songs...")
            self.stacked_widget.setCurrentIndex(4)

    # ==========================================
    # PAGE 1: HOME
    # ==========================================
    def build_home_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(25)

        welcome_header = QHBoxLayout()
        self.home_welcome_label = QLabel("Welcome back, User!")
        self.home_welcome_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        welcome_header.addWidget(self.home_welcome_label)
        welcome_header.addStretch()
        layout.addLayout(welcome_header)

        hero = QFrame()
        hero.setObjectName("HeroBanner")
        hero.setFixedHeight(220)
        h_layout = QHBoxLayout(hero)
        h_layout.setContentsMargins(20, 20, 20, 20)
        h_layout.setSpacing(25)
        h_art = QLabel()
        h_art.setFixedSize(180, 180)
        h_art.setStyleSheet("background: #333; border-radius: 8px;")
        h_text = QVBoxLayout()
        h_text.setAlignment(Qt.AlignVCenter)
        h_text.setSpacing(6)
        h_tag = QLabel("EDITOR'S PICK · ALBUM OF THE WEEK")
        h_tag.setStyleSheet("color: #ff5555; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        h_title = QLabel("On Giacometti — Hania Rani")
        h_title.setStyleSheet("color: white; font-size: 26px; font-weight: bold;")
        h_desc = QLabel("Recorded in the Swiss Alps, full of snow and silence and long reverb tails that invite meditative space for deep, uninterrupted listening.")
        h_desc.setWordWrap(True)
        h_desc.setStyleSheet("color: #aaa; font-size: 12px;")
        h_btn = QPushButton("▶ Play Album")
        h_btn.setFixedSize(110, 32)
        h_btn.setStyleSheet("background-color: #0055ff; color: white; border-radius: 16px; font-weight: bold; font-size: 11px;")
        h_text.addWidget(h_tag)
        h_text.addWidget(h_title)
        h_text.addWidget(h_desc)
        h_text.addSpacing(10)
        h_text.addWidget(h_btn, alignment=Qt.AlignLeft)
        h_layout.addWidget(h_art)
        h_layout.addLayout(h_text, 1)
        layout.addWidget(hero)

        jb_head = QHBoxLayout()
        jb_title = QLabel("Jump Back In")
        jb_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        jb_sub = QLabel("Recent listening history")
        jb_sub.setStyleSheet("color: #666; font-size: 10px;")
        jb_head.addWidget(jb_title)
        jb_head.addStretch()
        jb_head.addWidget(jb_sub)
        layout.addLayout(jb_head)

        jb_layout = QHBoxLayout()
        jb_layout.setSpacing(15)
        recents = [("Nils Frahm Radio", "Artist Mix"), ("Deep Focus Playlist", "42 tracks · Ambient"), ("All Melody", "Nils Frahm"), ("remember", "Ólafur Arnalds"), ("Eusa", "Hania Rani"), ("Singularity", "Jon Hopkins")]
        for title, sub in recents:
            card = QFrame()
            card.setFixedSize(150, 195)
            card.setStyleSheet("background-color: #181818; border-radius: 6px; border: 1px solid #222;")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(10, 10, 10, 10)
            c_layout.setSpacing(5)
            art = QLabel()
            art.setFixedSize(130, 130)
            art.setStyleSheet("background-color: #333; border-radius: 6px;")
            t = QLabel(title)
            t.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
            s = QLabel(sub)
            s.setStyleSheet("color: #888; font-size: 10px;")
            c_layout.addWidget(art, alignment=Qt.AlignCenter)
            c_layout.addWidget(t)
            c_layout.addWidget(s)
            jb_layout.addWidget(card)
        jb_layout.addStretch()
        layout.addLayout(jb_layout)

        mf_head = QHBoxLayout()
        mf_title = QLabel("Trending on Jamendo")
        mf_title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        tracks = jamendo_api.fetch_trending_tracks(limit=20)
        mf_count = QLabel(f"{len(tracks)} tracks")
        mf_count.setStyleSheet("color: #666; font-size: 10px;")
        mf_head.addWidget(mf_title)
        mf_head.addStretch()
        mf_head.addWidget(mf_count)
        layout.addLayout(mf_head)

        if not tracks:
            layout.addWidget(QLabel("Failed to load Jamendo tracks. Check terminal for details."))
        else:
            mf_grid = QGridLayout()
            mf_grid.setSpacing(15)
            for idx, track in enumerate(tracks):
                card = QFrame()
                card.setObjectName("MixCard")
                card.setFixedHeight(125)
                c_layout = QHBoxLayout(card)
                c_layout.setContentsMargins(12, 12, 12, 12)
                art_label = QLabel()
                art_label.setFixedSize(84, 84)
                art_label.setStyleSheet("background-color: #333; border-radius: 6px;")
                img_url = track.get("album_image") or track.get("image")
                pixmap = self._pixmap_from_url(img_url, 84, 84)
                if pixmap: art_label.setPixmap(pixmap)
                text_col = QVBoxLayout()
                text_col.setSpacing(3)
                top_meta = QHBoxLayout()
                tag = QLabel("TRACK")
                tag.setStyleSheet("color: #0055ff; font-size: 8px; font-weight: bold; letter-spacing: 0.5px;")
                dur_ms = max(0, int(track.get("duration") or 0) * 1000)
                dur_lbl = QLabel(self._format_time(dur_ms))
                dur_lbl.setStyleSheet("color: #777; font-size: 9px;")
                top_meta.addWidget(tag)
                top_meta.addStretch()
                top_meta.addWidget(dur_lbl)
                full_name = track.get("name", "Unknown Track")
                display_name = full_name if len(full_name) <= 18 else full_name[:16] + "..."
                t = QLabel(display_name)
                t.setToolTip(full_name)
                t.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
                artist_name = track.get("artist_name", "Unknown Artist")
                display_artist = artist_name if len(artist_name) <= 22 else artist_name[:20] + "..."
                s = QLabel(display_artist)
                s.setToolTip(artist_name)
                s.setStyleSheet("color: #888; font-size: 10px;")
                text_col.addLayout(top_meta)
                text_col.addWidget(t)
                text_col.addWidget(s)
                text_col.addStretch()
                actions_col = QVBoxLayout()
                actions_col.setSpacing(6)
                actions_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                heart_btn = QPushButton("♡")
                heart_btn.setFixedSize(24, 24)
                heart_btn.setCursor(Qt.PointingHandCursor)
                self._apply_heart_style(heart_btn, self._is_liked(track))
                heart_btn.clicked.connect(lambda checked, tr=track: self.toggle_like_track(tr))
                self.home_heart_buttons.append((heart_btn, track))
                play_btn = QPushButton("▶")
                play_btn.setFixedSize(26, 26)
                play_btn.setCursor(Qt.PointingHandCursor)
                play_btn.setStyleSheet("background-color: #1a1a1a; color: #0055ff; border-radius: 13px; font-weight: bold; font-size: 10px;")
                audio_url = track.get("audio")
                if audio_url:
                    self.home_play_buttons.append((play_btn, audio_url))
                    self.home_duration_labels.append((dur_lbl, audio_url))
                    play_btn.clicked.connect(lambda checked, tr=track, pl=tracks, i=idx: self.play_track(tr, pl, i))
                actions_col.addWidget(heart_btn, alignment=Qt.AlignRight)
                actions_col.addStretch()
                actions_col.addWidget(play_btn, alignment=Qt.AlignRight)
                c_layout.addWidget(art_label)
                c_layout.addSpacing(8)
                c_layout.addLayout(text_col, 1)
                c_layout.addLayout(actions_col)
                mf_grid.addWidget(card, idx // 4, idx % 4)
            for col in range(4): mf_grid.setColumnStretch(col, 1)
            layout.addLayout(mf_grid)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ==========================================
    # PAGE 3: VIDEO
    # ==========================================
    def build_video_page(self):
        """Embeds the movie browser in the Video tab."""
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.video_hub = VideoHub()
        self.video_hub.setMinimumSize(0, 0)
        self.video_hub.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_welcome_label = self.video_hub.welcome_label
        layout.addWidget(self.video_hub)
        return wrapper

    # ==========================================
    # VECTOR PLAYER ICONS & UTILS
    # ==========================================
    def _new_icon_canvas(self, size):
        pixmap = QPixmap(size * 2, size * 2)
        pixmap.setDevicePixelRatio(2.0)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        return pixmap, painter

    def _make_prev_icon(self, size=18, color="#b3b3b3"):
        pixmap, p = self._new_icon_canvas(size)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(color)))
        bar_w = size * 0.12
        margin = size * 0.18
        p.drawRect(int(margin), int(margin), max(2, int(bar_w)), int(size - 2 * margin))
        tri = QPolygonF([QPointF(size - margin, margin), QPointF(margin + bar_w + 1, size * 0.5), QPointF(size - margin, size - margin)])
        p.drawPolygon(tri)
        p.end()
        return QIcon(pixmap)

    def _make_next_icon(self, size=18, color="#b3b3b3"):
        pixmap, p = self._new_icon_canvas(size)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(color)))
        bar_w = size * 0.12
        margin = size * 0.18
        tri = QPolygonF([QPointF(margin, margin), QPointF(size - margin - bar_w - 1, size * 0.5), QPointF(margin, size - margin)])
        p.drawPolygon(tri)
        p.drawRect(int(size - margin - bar_w), int(margin), max(2, int(bar_w)), int(size - 2 * margin))
        p.end()
        return QIcon(pixmap)

    def _make_play_icon(self, size=16, color="#000000"):
        pixmap, p = self._new_icon_canvas(size)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(color)))
        tri = QPolygonF([QPointF(size * 0.28, size * 0.16), QPointF(size * 0.84, size * 0.5), QPointF(size * 0.28, size * 0.84)])
        p.drawPolygon(tri)
        p.end()
        return QIcon(pixmap)

    def _make_pause_icon(self, size=16, color="#000000"):
        pixmap, p = self._new_icon_canvas(size)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(color)))
        bar_w = max(2, int(size * 0.18))
        h = int(size * 0.66)
        y = int(size * 0.17)
        p.drawRect(int(size * 0.24), y, bar_w, h)
        p.drawRect(int(size * 0.58), y, bar_w, h)
        p.end()
        return QIcon(pixmap)

    def _make_volume_icon(self, size=16, color="#b3b3b3", muted=False):
        pixmap, p = self._new_icon_canvas(size)
        pen = QPen(QColor(color))
        pen.setWidthF(1.5)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        speaker = QPolygonF([QPointF(2.0, 6.0), QPointF(5.0, 6.0), QPointF(8.5, 3.0), QPointF(8.5, 13.0), QPointF(5.0, 10.0), QPointF(2.0, 10.0)])
        p.drawPolygon(speaker)
        if muted:
            p.drawLine(QPointF(11.0, 5.5), QPointF(14.5, 10.5))
            p.drawLine(QPointF(14.5, 5.5), QPointF(11.0, 10.5))
        else:
            p.drawArc(7, 4, 5, 8, -55 * 16, 110 * 16)
            p.drawArc(7, 2, 8, 12, -55 * 16, 110 * 16)
        p.end()
        return QIcon(pixmap)

    def _update_nav_pills(self, active_index):
        active_style = "QPushButton { background-color: #ffffff; color: #000000; border: none; border-radius: 16px; padding: 6px 16px; font-size: 12px; font-weight: bold; }"
        inactive_style = "QPushButton { background-color: #242424; color: #ffffff; border: none; border-radius: 16px; padding: 6px 16px; font-size: 12px; font-weight: 500; } QPushButton:hover { background-color: #333333; }"
        for i, btn in enumerate(self.nav_buttons):
            btn.setStyleSheet(active_style if i == active_index else inactive_style)

    def set_page(self, index):
        self.current_music_page = index
        self.stacked_widget.setCurrentIndex(index)
        self._update_nav_pills(index)

    def _pixmap_from_url(self, url, width, height):
        if not url: return None
        pixmap = self._pixmap_cache.get(url)
        if pixmap is None:
            pixmap = jamendo_api.download_image(url)
            if pixmap: self._pixmap_cache[url] = pixmap
        if pixmap: return pixmap.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        return None

    def _track_key(self, track):
        return track.get("audio") or str(track.get("id") or "")

    def _is_liked(self, track):
        key = self._track_key(track)
        return bool(key) and any(self._track_key(t) == key for t in self.liked_tracks)

    def _apply_heart_style(self, btn, liked):
        btn.setText("♥" if liked else "♡")
        btn.setStyleSheet("background: transparent; border: none; color: #ff5555; font-size: 14px;" if liked else "background: transparent; border: none; color: #888; font-size: 14px;")

    def _sync_heart_buttons(self):
        for btn, track in self.home_heart_buttons + self.search_heart_buttons + self.library_heart_buttons:
            self._apply_heart_style(btn, self._is_liked(track))
        if hasattr(self, "player_like_btn"):
            if self.current_track:
                self.player_like_btn.setEnabled(True)
                self._apply_heart_style(self.player_like_btn, self._is_liked(self.current_track))
            else:
                self.player_like_btn.setEnabled(False)
                self._apply_heart_style(self.player_like_btn, False)

    def toggle_like_track(self, track):
        if not track: return
        key = self._track_key(track)
        if not key: return
        existing_idx = next((i for i, t in enumerate(self.liked_tracks) if self._track_key(t) == key), None)
        if existing_idx is not None: self.liked_tracks.pop(existing_idx)
        else: self.liked_tracks.insert(0, dict(track))
        self._sync_heart_buttons()
        self._refresh_library_liked_songs()

    def _record_recently_played(self, track):
        key = self._track_key(track)
        if not key: return
        self.recently_played = [t for t in self.recently_played if self._track_key(t) != key]
        self.recently_played.insert(0, dict(track))
        self.recently_played = self.recently_played[:12]
        self._refresh_library_recently_played()

    def play_track(self, track, playlist=None, index=0):
        audio_url = track.get("audio")
        track_name = track.get("name", "Unknown Track")
        artist_name = track.get("artist_name", "Unknown Artist")
        duration_sec = track.get("duration", 0)
        img_url = track.get("album_image") or track.get("image")
        if playlist is not None:
            self.current_playlist = list(playlist)
            self.current_index = index
        self.current_track = dict(track)
        self.play_jamendo_track(audio_url, track_name, artist_name, duration_sec=duration_sec, img_url=img_url, track_obj=track)

    def play_jamendo_track(self, audio_url, track_name, artist_name, duration_sec=0, img_url=None, track_obj=None):
        if not audio_url or not audio_url.startswith("http"):
            return
        same_track = self.current_audio_url == audio_url
        if same_track and self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            return
        if not same_track:
            self.current_audio_url = audio_url
            if track_obj is not None: self.current_track = dict(track_obj)
            else:
                self.current_track = {"audio": audio_url, "name": track_name, "artist_name": artist_name, "duration": duration_sec, "album_image": img_url}
            self.player_title.setText(track_name)
            self.player_artist.setText(artist_name or "Unknown Artist")
            scaled_art = self._pixmap_from_url(img_url, 50, 50)
            if scaled_art: self.player_art.setPixmap(scaled_art)
            else: self.player_art.clear()
            self._expected_duration_ms = max(0, int(duration_sec or 0) * 1000)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setRange(0, self._expected_duration_ms)
            self.progress_slider.setValue(0)
            self.progress_slider.blockSignals(False)
            self.time_now.setText("00:00")
            self.time_total.setText(self._format_time(self._expected_duration_ms))
            self._sync_heart_buttons()
            self._record_recently_played(self.current_track)
            self.media_player.setSource(QUrl(audio_url))
        self.media_player.play()

    def play_previous_track(self):
        if not self.current_playlist: return
        if self.media_player.position() > 3000:
            self.media_player.setPosition(0)
            return
        if self.current_index > 0:
            new_idx = self.current_index - 1
            self.play_track(self.current_playlist[new_idx], self.current_playlist, new_idx)

    def play_next_track(self):
        if not self.current_playlist: return
        if self.current_index + 1 < len(self.current_playlist):
            new_idx = self.current_index + 1
            self.play_track(self.current_playlist[new_idx], self.current_playlist, new_idx)

    def toggle_play_pause(self):
        if not self.current_audio_url: return
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.media_player.pause()
        else: self.media_player.play()

    def _refresh_play_buttons(self, playing):
        if hasattr(self, "play_pause_btn"):
            self.play_pause_btn.setIcon(self._pause_icon if playing else self._play_icon)
        for btn, url in self.home_play_buttons + self.search_play_buttons + self.library_play_buttons:
            btn.setText("⏸" if playing and url == self.current_audio_url else "▶")

    def _on_playback_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._refresh_play_buttons(playing)

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia: self.play_next_track()

    def _format_time(self, ms):
        seconds = max(0, int(ms // 1000))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _on_position_changed(self, position):
        if self._seeking or not hasattr(self, "progress_slider"): return
        if position > self.progress_slider.maximum(): self.progress_slider.setMaximum(position)
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(position)
        self.progress_slider.blockSignals(False)
        self.time_now.setText(self._format_time(position))

    def _on_duration_changed(self, duration):
        if not hasattr(self, "progress_slider"): return
        effective_duration = duration if duration > 0 else self._expected_duration_ms
        self.progress_slider.setMaximum(max(effective_duration, 0))
        self.time_total.setText(self._format_time(effective_duration))
        if duration > 0:
            formatted = self._format_time(duration)
            for lbl, url in self.home_duration_labels + self.search_duration_labels + self.library_duration_labels:
                if url == self.current_audio_url: lbl.setText(formatted)

    def _on_seek_pressed(self): self._seeking = True
    def _on_seek_released(self):
        self._seeking = False
        self.media_player.setPosition(self.progress_slider.value())
    def _on_seek_moved(self, value): self.time_now.setText(self._format_time(value))

    def _on_volume_changed(self, value):
        self.audio_output.setVolume(value / 100)
        if value > 0: self._last_volume = value
        if hasattr(self, "vol_btn"): self.vol_btn.setIcon(self._vol_muted_icon if value == 0 else self._vol_icon)

    def _toggle_mute(self):
        if self.vol_slider.value() > 0:
            self._last_volume = self.vol_slider.value()
            self.vol_slider.setValue(0)
        else: self.vol_slider.setValue(self._last_volume or 80)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None: widget.deleteLater()
            elif child_layout is not None: self._clear_layout(child_layout)

    # ==========================================
    # PAGE 2: SEARCH
    # ==========================================
    def build_search_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(16)
        search_wrapper = QHBoxLayout()
        search_wrapper.addStretch()
        self.big_search = QLineEdit()
        self.big_search.setObjectName("SearchBar")
        self.big_search.setPlaceholderText("Search artists, songs, or tags...")
        self.big_search.setFixedSize(420, 38)
        self.big_search.setStyleSheet("font-size: 12px; padding-left: 15px; padding-right: 36px; border-radius: 6px; background-color: #1a1a1a; border: 1px solid #333;")
        self.big_search.textChanged.connect(self._on_big_search_text_changed)
        self.big_search.returnPressed.connect(self._on_big_search_submit)
        clear_btn = QPushButton("✕")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("background: transparent; color: #888; border: none; font-size: 12px;")
        clear_btn.clicked.connect(self._clear_search)
        sbl = QHBoxLayout(self.big_search)
        sbl.setContentsMargins(0, 0, 12, 0)
        sbl.addStretch()
        sbl.addWidget(clear_btn)
        search_go_btn = QPushButton("Search")
        search_go_btn.setFixedHeight(38)
        search_go_btn.setCursor(Qt.PointingHandCursor)
        search_go_btn.setStyleSheet("background-color: #0055ff; color: white; border-radius: 6px; padding: 0 16px; font-weight: bold; font-size: 12px;")
        search_go_btn.clicked.connect(self._on_big_search_submit)
        search_wrapper.addWidget(self.big_search)
        search_wrapper.addSpacing(8)
        search_wrapper.addWidget(search_go_btn)
        search_wrapper.addStretch()
        filter_wrapper = QHBoxLayout()
        filter_wrapper.addStretch()
        self.search_filter_buttons = {}
        for f in ["ALL", "ARTISTS", "SONGS"]:
            btn = QPushButton(f)
            btn.setObjectName("FilterBtnActive" if f == self.search_filter else "FilterBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, mode=f: self._set_search_filter(mode))
            filter_wrapper.addWidget(btn)
            self.search_filter_buttons[f] = btn
        filter_wrapper.addStretch()
        layout.addLayout(search_wrapper)
        layout.addLayout(filter_wrapper)
        self.search_history_section = QWidget()
        sh_outer = QVBoxLayout(self.search_history_section)
        sh_outer.setContentsMargins(0, 0, 0, 0)
        sh_outer.setSpacing(8)
        sh_header = QHBoxLayout()
        sh_title = QLabel("SEARCH HISTORY")
        sh_title.setObjectName("SectionTitle")
        sh_clear_btn = QPushButton("Clear")
        sh_clear_btn.setCursor(Qt.PointingHandCursor)
        sh_clear_btn.setStyleSheet("background: transparent; border: none; color: #777; font-size: 11px;")
        sh_clear_btn.clicked.connect(self._clear_search_history)
        sh_header.addWidget(sh_title)
        sh_header.addStretch()
        sh_header.addWidget(sh_clear_btn)
        self.search_history_chips_layout = QHBoxLayout()
        self.search_history_chips_layout.setSpacing(8)
        sh_outer.addLayout(sh_header)
        sh_outer.addLayout(self.search_history_chips_layout)
        layout.addWidget(self.search_history_section)
        self._refresh_search_history_ui()
        self.search_status_label = QLabel("Type to search Jamendo for artists and songs.")
        self.search_status_label.setAlignment(Qt.AlignCenter)
        self.search_status_label.setStyleSheet("color: #777; font-size: 11px;")
        layout.addWidget(self.search_status_label)
        self.search_results_layout = QVBoxLayout()
        self.search_results_layout.setSpacing(16)
        layout.addLayout(self.search_results_layout)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _open_profile_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #141414; color: white; border: 1px solid #2a2a2a; "
            "border-radius: 8px; padding: 6px; }"
            "QMenu::item { padding: 8px 18px; border-radius: 6px; }"
            "QMenu::item:selected { background-color: #0055ff; }"
            "QMenu::item:disabled { color: #9aa0a6; }"
            "QMenu::separator { height: 1px; background: #2a2a2a; margin: 4px 8px; }"
        )
        account = menu.addAction(self.username or "Account")
        account.setEnabled(False)
        menu.addSeparator()
        logout_action = menu.addAction("Log out")
        logout_action.triggered.connect(self.logout)
        menu.exec(self.profile_label.mapToGlobal(self.profile_label.rect().bottomLeft()))

    def logout(self):
        answer = QMessageBox.question(
            self,
            "Log out",
            f"Log out of {self.username}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.stop()
        if self.receivers(self.logout_requested) == 0:
            from login import LoginWindow
            self._login_window = LoginWindow()
            self._login_window.prepare_for_login()
            self._login_window.show()
        else:
            self.logout_requested.emit()
        self.close()

    def _on_header_search(self):
        query = self.header_search.text().strip()
        if not query:
            return
        if self.stacked_widget.currentIndex() == 3 and hasattr(self, "video_hub"):
            self.video_hub._on_search(query)
            return
        self._set_top_mode(0)
        self.set_page(1)
        self._quick_search(query)

    def _on_big_search_text_changed(self, text):
        query = text.strip()
        if not query:
            self.search_debounce_timer.stop()
            self._search_request_id += 1
            self.last_search_results = None
            self._clear_search_results_ui()
            self.search_status_label.setText("Type to search Jamendo for artists and songs.")
            self.search_status_label.show()
            return
        self.search_debounce_timer.start()

    def _on_big_search_submit(self):
        self.search_debounce_timer.stop()
        self.run_search(self.big_search.text())

    def _quick_search(self, query):
        self.search_debounce_timer.stop()
        self.big_search.blockSignals(True)
        self.big_search.setText(query)
        self.big_search.blockSignals(False)
        self.run_search(query)

    def _clear_search(self):
        self.search_debounce_timer.stop()
        self._search_request_id += 1
        self.big_search.blockSignals(True)
        self.big_search.clear()
        self.big_search.blockSignals(False)
        self.last_search_results = None
        self._clear_search_results_ui()
        self.search_status_label.setText("Type to search Jamendo for artists and songs.")
        self.search_status_label.show()

    def _add_search_history(self, query):
        clean = (query or "").strip()
        if not clean: return
        self.search_history = [h for h in self.search_history if h.lower() != clean.lower()]
        self.search_history.insert(0, clean)
        self.search_history = self.search_history[:10]
        self._refresh_search_history_ui()

    def _clear_search_history(self):
        self.search_history.clear()
        self._refresh_search_history_ui()

    def _refresh_search_history_ui(self):
        self._clear_layout(self.search_history_chips_layout)
        if not self.search_history:
            self.search_history_section.hide()
            return
        self.search_history_section.show()
        for query in self.search_history:
            chip = QPushButton(query)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setStyleSheet("background-color: #1a1a1a; color: #ddd; border: 1px solid #333; border-radius: 14px; padding: 4px 12px; font-size: 11px;")
            chip.clicked.connect(lambda checked, q=query: self._quick_search(q))
            self.search_history_chips_layout.addWidget(chip)
        self.search_history_chips_layout.addStretch()

    def _set_search_filter(self, mode):
        self.search_filter = mode
        for f, btn in self.search_filter_buttons.items():
            btn.setObjectName("FilterBtnActive" if f == mode else "FilterBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if self.last_search_results is not None:
            self._render_search_results(self.last_search_results)

    def run_search(self, query):
        query = (query or "").strip()
        if not query:
            self._clear_search()
            return
        self._search_request_id += 1
        request_id = self._search_request_id
        self.search_status_label.setText(f'Searching Jamendo for "{query}"...')
        self.search_status_label.show()
        worker = SearchWorker(request_id, query)
        self._active_workers.add(worker)
        worker.finished_search.connect(self._on_search_finished)
        worker.finished.connect(lambda w=worker: self._active_workers.discard(w))
        worker.start()

    def _on_search_finished(self, request_id, query, results, image_bytes):
        if request_id != self._search_request_id: return
        for url, raw in image_bytes.items():
            if url not in self._pixmap_cache:
                img = QImage()
                if img.loadFromData(QByteArray(raw)):
                    self._pixmap_cache[url] = QPixmap(img)
        self._add_search_history(query)
        self.last_search_results = results
        self._render_search_results(results)

    def _clear_search_results_ui(self):
        self.search_play_buttons.clear()
        self.search_duration_labels.clear()
        self.search_heart_buttons.clear()
        self._clear_layout(self.search_results_layout)

    def _render_search_results(self, results):
        self._clear_search_results_ui()
        artists = results.get("artists", [])
        tracks = results.get("tracks", [])
        show_artists = self.search_filter in ("ALL", "ARTISTS")
        show_songs = self.search_filter in ("ALL", "SONGS")
        if (not show_artists or not artists) and (not show_songs or not tracks):
            self.search_status_label.setText("No matching artists or playable songs found.")
            self.search_status_label.show()
            return
        self.search_status_label.hide()
        if show_artists and artists:
            artists_lbl = QLabel(f"ARTISTS ({len(artists)})")
            artists_lbl.setObjectName("SectionTitle")
            self.search_results_layout.addWidget(artists_lbl)
            for artist in artists:
                artist_tracks = artist.get("tracks", [])
                artist_card = QFrame()
                artist_card.setObjectName("TableContainer")
                ac_layout = QHBoxLayout(artist_card)
                ac_layout.setContentsMargins(20, 18, 20, 18)
                ac_layout.setSpacing(20)
                art_img = QLabel()
                art_img.setFixedSize(130, 130)
                art_img.setStyleSheet("background-color: #333; border-radius: 6px;")
                pixmap = self._pixmap_from_url(artist.get("image"), 130, 130)
                if pixmap: art_img.setPixmap(pixmap)
                info_layout = QVBoxLayout()
                info_layout.setAlignment(Qt.AlignVCenter)
                artist_tag = QLabel("ARTIST")
                artist_tag.setStyleSheet("color: #ff5555; font-size: 9px; font-weight: bold;")
                artist_name_lbl = QLabel(artist.get("name", "Unknown Artist"))
                artist_name_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
                artist_name_lbl.setWordWrap(True)
                track_count = len(artist_tracks)
                artist_stats = QLabel(f"{track_count} playable song{'s' if track_count != 1 else ''}")
                artist_stats.setStyleSheet("color: #aaa; font-size: 11px;")
                info_layout.addWidget(artist_tag)
                info_layout.addWidget(artist_name_lbl)
                info_layout.addWidget(artist_stats)
                main_play_btn = QPushButton()
                main_play_btn.setFixedSize(44, 44)
                main_play_btn.setCursor(Qt.PointingHandCursor)
                main_play_btn.setStyleSheet("QPushButton { background-color: #ffffff; border: none; border-radius: 22px; } QPushButton:hover { background-color: #e6e6e6; } QPushButton:disabled { background-color: #333333; }")
                main_play_btn.setIcon(self._make_play_icon(18, "#000000"))
                main_play_btn.setIconSize(QSize(18, 18))
                if artist_tracks: main_play_btn.clicked.connect(lambda checked, tr=artist_tracks[0], pl=artist_tracks: self.play_track(tr, pl, 0))
                else: main_play_btn.setEnabled(False)
                tracks_layout = QVBoxLayout()
                tracks_layout.setSpacing(10)
                if not artist_tracks:
                    empty_lbl = QLabel("No playable tracks available for this artist.")
                    empty_lbl.setStyleSheet("color: #777; font-size: 11px;")
                    tracks_layout.addWidget(empty_lbl)
                else:
                    for idx, tr in enumerate(artist_tracks):
                        t_row = QHBoxLayout()
                        t_play = QPushButton("▶")
                        t_play.setFixedSize(22, 22)
                        t_play.setCursor(Qt.PointingHandCursor)
                        t_play.setStyleSheet("background: transparent; color: #aaa; border: none; font-size: 10px;")
                        t_name = QLabel(tr.get("name", "Unknown Track"))
                        t_name.setStyleSheet("color: white; font-size: 12px;")
                        t_album = QLabel(tr.get("album_name") or "Single")
                        t_album.setStyleSheet("color: #888; font-size: 11px;")
                        dur_ms = max(0, int(tr.get("duration") or 0) * 1000)
                        t_time = QLabel(self._format_time(dur_ms))
                        t_time.setStyleSheet("color: #888; font-size: 11px;")
                        t_heart = QPushButton("♡")
                        t_heart.setCursor(Qt.PointingHandCursor)
                        self._apply_heart_style(t_heart, self._is_liked(tr))
                        t_heart.clicked.connect(lambda checked, item=tr: self.toggle_like_track(item))
                        self.search_heart_buttons.append((t_heart, tr))
                        audio_url = tr.get("audio")
                        if audio_url:
                            self.search_play_buttons.append((t_play, audio_url))
                            self.search_duration_labels.append((t_time, audio_url))
                            t_play.clicked.connect(lambda checked, item=tr, pl=artist_tracks, i=idx: self.play_track(item, pl, i))
                        t_row.addWidget(t_play)
                        t_row.addWidget(t_name, 1)
                        t_row.addWidget(t_album, 1)
                        t_row.addWidget(t_time)
                        t_row.addSpacing(8)
                        t_row.addWidget(t_heart)
                        tracks_layout.addLayout(t_row)
                ac_layout.addWidget(art_img)
                ac_layout.addLayout(info_layout, 1)
                ac_layout.addWidget(main_play_btn)
                ac_layout.addLayout(tracks_layout, 2)
                self.search_results_layout.addWidget(artist_card)
        if show_songs and tracks:
            songs_lbl = QLabel(f"SONGS ({len(tracks)})")
            songs_lbl.setObjectName("SectionTitle")
            self.search_results_layout.addWidget(songs_lbl)
            songs_container = QFrame()
            songs_container.setObjectName("TableContainer")
            sc_layout = QVBoxLayout(songs_container)
            sc_layout.setContentsMargins(16, 12, 16, 12)
            sc_layout.setSpacing(6)
            for idx, tr in enumerate(tracks):
                row = self._build_song_row(tr, tracks, idx, self.search_play_buttons, self.search_duration_labels, self.search_heart_buttons)
                sc_layout.addWidget(row)
            self.search_results_layout.addWidget(songs_container)
        playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self._refresh_play_buttons(playing)

    def _build_song_row(self, tr, playlist, idx, play_list, dur_list, heart_list):
        row = QFrame()
        row.setObjectName("PlaylistRow")
        r_layout = QHBoxLayout(row)
        r_layout.setContentsMargins(4, 6, 4, 6)
        r_layout.setSpacing(12)
        play_btn = QPushButton("▶")
        play_btn.setFixedSize(26, 26)
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setStyleSheet("background-color: #222; color: #0055ff; border: none; border-radius: 13px; font-size: 10px;")
        thumb = QLabel()
        thumb.setFixedSize(36, 36)
        thumb.setStyleSheet("background-color: #333; border-radius: 4px;")
        img_url = tr.get("album_image") or tr.get("image")
        pixmap = self._pixmap_from_url(img_url, 36, 36)
        if pixmap: thumb.setPixmap(pixmap)
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_lbl = QLabel(tr.get("name", "Unknown Track"))
        title_lbl.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
        artist_lbl = QLabel(tr.get("artist_name", "Unknown Artist"))
        artist_lbl.setStyleSheet("color: #888; font-size: 10px;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(artist_lbl)
        album_lbl = QLabel(tr.get("album_name") or "Single")
        album_lbl.setStyleSheet("color: #777; font-size: 11px;")
        dur_ms = max(0, int(tr.get("duration") or 0) * 1000)
        dur_lbl = QLabel(self._format_time(dur_ms))
        dur_lbl.setStyleSheet("color: #888; font-size: 11px;")
        heart_btn = QPushButton("♡")
        heart_btn.setCursor(Qt.PointingHandCursor)
        self._apply_heart_style(heart_btn, self._is_liked(tr))
        heart_btn.clicked.connect(lambda checked, item=tr: self.toggle_like_track(item))
        heart_list.append((heart_btn, tr))
        audio_url = tr.get("audio")
        if audio_url:
            play_list.append((play_btn, audio_url))
            dur_list.append((dur_lbl, audio_url))
            play_btn.clicked.connect(lambda checked, item=tr, pl=playlist, i=idx: self.play_track(item, pl, i))
        r_layout.addWidget(play_btn)
        r_layout.addWidget(thumb)
        r_layout.addLayout(title_col, 2)
        r_layout.addWidget(album_lbl, 1)
        r_layout.addWidget(dur_lbl)
        r_layout.addWidget(heart_btn)
        return row

    # ==========================================
    # PAGE 3: LIBRARY
    # ==========================================
    def build_library_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(20)
        title_row = QHBoxLayout()
        title = QLabel("Your Library")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch()
        self.library_filter_buttons = {}
        for f in ["All", "Liked Songs", "Recently Played"]:
            btn = QPushButton(f)
            btn.setObjectName("FilterBtnActive" if f == self.library_filter else "FilterBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, mode=f: self._set_library_filter(mode))
            title_row.addWidget(btn)
            self.library_filter_buttons[f] = btn
        layout.addLayout(title_row)
        self.liked_section_widget = QWidget()
        liked_section_layout = QVBoxLayout(self.liked_section_widget)
        liked_section_layout.setContentsMargins(0, 0, 0, 0)
        liked_section_layout.setSpacing(12)
        liked_banner = QFrame()
        liked_banner.setObjectName("LikedBanner")
        liked_banner.setFixedHeight(120)
        lb_layout = QHBoxLayout(liked_banner)
        lb_layout.setContentsMargins(20, 20, 20, 20)
        heart_box = QFrame()
        heart_box.setFixedSize(80, 80)
        heart_box.setStyleSheet("background-color: white; border-radius: 8px;")
        hb_layout = QVBoxLayout(heart_box)
        hb_layout.setAlignment(Qt.AlignCenter)
        heart_icon = QLabel("♥")
        heart_icon.setStyleSheet("color: #0055ff; font-size: 36px; background: transparent;")
        hb_layout.addWidget(heart_icon)
        lb_text = QVBoxLayout()
        lb_text.setAlignment(Qt.AlignVCenter)
        lb_tag = QLabel("FAVORITES")
        lb_tag.setStyleSheet("color: #ccc; font-size: 9px; font-weight: bold; background: transparent;")
        lb_title = QLabel("Liked Songs")
        lb_title.setStyleSheet("color: white; font-size: 22px; font-weight: bold; background: transparent;")
        self.liked_banner_sub = QLabel("0 liked songs")
        self.liked_banner_sub.setStyleSheet("color: #eee; font-size: 10px; background: transparent;")
        lb_text.addWidget(lb_tag)
        lb_text.addWidget(lb_title)
        lb_text.addWidget(self.liked_banner_sub)
        self.liked_banner_play_btn = QPushButton()
        self.liked_banner_play_btn.setFixedSize(40, 40)
        self.liked_banner_play_btn.setCursor(Qt.PointingHandCursor)
        self.liked_banner_play_btn.setStyleSheet("QPushButton { background-color: white; border: none; border-radius: 20px; } QPushButton:hover { background-color: #e6e6e6; } QPushButton:disabled { background-color: #cccccc; }")
        self.liked_banner_play_btn.setIcon(self._make_play_icon(16, "#0055ff"))
        self.liked_banner_play_btn.setIconSize(QSize(16, 16))
        self.liked_banner_play_btn.clicked.connect(self._play_liked_songs)
        lb_layout.addWidget(heart_box)
        lb_layout.addSpacing(15)
        lb_layout.addLayout(lb_text, 1)
        lb_layout.addWidget(self.liked_banner_play_btn)
        liked_section_layout.addWidget(liked_banner)
        self.liked_songs_container = QVBoxLayout()
        self.liked_songs_container.setSpacing(6)
        liked_section_layout.addLayout(self.liked_songs_container)
        layout.addWidget(self.liked_section_widget)
        self.recent_section_widget = QWidget()
        recent_section_layout = QVBoxLayout(self.recent_section_widget)
        recent_section_layout.setContentsMargins(0, 0, 0, 0)
        recent_section_layout.setSpacing(12)
        rp_title = QLabel("Recently Played")
        rp_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        recent_section_layout.addWidget(rp_title)
        self.rp_container_layout = QVBoxLayout()
        self.rp_container_layout.setSpacing(10)
        recent_section_layout.addLayout(self.rp_container_layout)
        layout.addWidget(self.recent_section_widget)
        self._refresh_library_liked_songs()
        self._refresh_library_recently_played()
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _set_library_filter(self, mode):
        self.library_filter = mode
        for f, btn in self.library_filter_buttons.items():
            btn.setObjectName("FilterBtnActive" if f == mode else "FilterBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.liked_section_widget.setVisible(mode in ("All", "Liked Songs"))
        self.recent_section_widget.setVisible(mode in ("All", "Recently Played"))

    def _play_liked_songs(self):
        if self.liked_tracks: self.play_track(self.liked_tracks[0], self.liked_tracks, 0)

    def _refresh_library_liked_songs(self):
        self.library_play_buttons.clear()
        self.library_duration_labels.clear()
        self.library_heart_buttons.clear()
        self._clear_layout(self.liked_songs_container)
        count = len(self.liked_tracks)
        if count == 0:
            self.liked_banner_sub.setText("0 liked songs")
            self.liked_banner_play_btn.setEnabled(False)
            empty_lbl = QLabel("No liked songs yet. Click ♡ on any track to add it here.")
            empty_lbl.setStyleSheet("color: #777; font-size: 11px; padding: 6px 0;")
            self.liked_songs_container.addWidget(empty_lbl)
            return
        latest = self.liked_tracks[0]
        self.liked_banner_sub.setText(f"{count} liked song{'s' if count != 1 else ''} · Latest: {latest.get('name', '')} by {latest.get('artist_name', '')}")
        self.liked_banner_play_btn.setEnabled(True)
        table = QFrame()
        table.setObjectName("TableContainer")
        t_layout = QVBoxLayout(table)
        t_layout.setContentsMargins(16, 12, 16, 12)
        t_layout.setSpacing(6)
        for idx, tr in enumerate(self.liked_tracks):
            row = self._build_song_row(tr, self.liked_tracks, idx, self.library_play_buttons, self.library_duration_labels, self.library_heart_buttons)
            t_layout.addWidget(row)
        self.liked_songs_container.addWidget(table)
        playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        self._refresh_play_buttons(playing)

    def _refresh_library_recently_played(self):
        self._clear_layout(self.rp_container_layout)
        if not self.recently_played:
            empty_lbl = QLabel("No recently played songs yet. Play a track to see it here.")
            empty_lbl.setStyleSheet("color: #777; font-size: 11px; padding: 4px 0;")
            self.rp_container_layout.addWidget(empty_lbl)
            return
        grid = QGridLayout()
        grid.setSpacing(15)
        for idx, tr in enumerate(self.recently_played):
            card = ClickableFrame()
            card.setObjectName("RecentCard")
            card.setFixedHeight(64)
            card.setCursor(Qt.PointingHandCursor)
            card.clicked.connect(lambda item=tr, pl=self.recently_played, i=idx: self.play_track(item, pl, i))
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(8, 7, 12, 7)
            c_layout.setSpacing(10)
            art = QLabel()
            art.setFixedSize(50, 50)
            art.setStyleSheet("background-color: #222; border-radius: 4px;")
            img_url = tr.get("album_image") or tr.get("image")
            pixmap = self._pixmap_from_url(img_url, 50, 50)
            if pixmap: art.setPixmap(pixmap)
            info = QVBoxLayout()
            info.setSpacing(2)
            info.setAlignment(Qt.AlignVCenter)
            full_name = tr.get("name", "Unknown Track")
            display_name = full_name if len(full_name) <= 22 else full_name[:20] + "..."
            t = QLabel(display_name)
            t.setToolTip(full_name)
            t.setStyleSheet("color: white; font-size: 11px; font-weight: bold;")
            artist_name = tr.get("artist_name", "Unknown Artist")
            dur_ms = max(0, int(tr.get("duration") or 0) * 1000)
            s = QLabel(f"{artist_name} · {self._format_time(dur_ms)}")
            s.setStyleSheet("color: #888; font-size: 10px;")
            info.addWidget(t)
            info.addWidget(s)
            c_layout.addWidget(art)
            c_layout.addLayout(info, 1)
            grid.addWidget(card, idx // 4, idx % 4)
        for col in range(4): grid.setColumnStretch(col, 1)
        self.rp_container_layout.addLayout(grid)

    # ==========================================
    # PLAYER BAR
    # ==========================================
    def create_player_bar(self):
        player_bar = QWidget()
        player_bar.setObjectName("PlayerBar")
        player_bar.setFixedHeight(80)
        layout = QHBoxLayout(player_bar)
        layout.setContentsMargins(20, 10, 20, 10)
        self._play_icon = self._make_play_icon(16, "#000000")
        self._pause_icon = self._make_pause_icon(16, "#000000")
        self._vol_icon = self._make_volume_icon(16, "#b3b3b3", muted=False)
        self._vol_muted_icon = self._make_volume_icon(16, "#b3b3b3", muted=True)
        left = QHBoxLayout()
        self.player_art = QLabel()
        self.player_art.setFixedSize(50, 50)
        self.player_art.setStyleSheet("background-color: #222; border-radius: 4px;")
        info = QVBoxLayout()
        info.setSpacing(2)
        self.player_title = QLabel("Select a track")
        self.player_title.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        self.player_artist = QLabel("Jamendo")
        self.player_artist.setStyleSheet("color: #888; font-size: 10px;")
        info.addWidget(self.player_title)
        info.addWidget(self.player_artist)
        self.player_like_btn = QPushButton("♡")
        self.player_like_btn.setFixedSize(28, 28)
        self.player_like_btn.setCursor(Qt.PointingHandCursor)
        self.player_like_btn.setEnabled(False)
        self._apply_heart_style(self.player_like_btn, False)
        self.player_like_btn.clicked.connect(lambda: self.toggle_like_track(self.current_track))
        left.addWidget(self.player_art)
        left.addSpacing(10)
        left.addLayout(info)
        left.addSpacing(8)
        left.addWidget(self.player_like_btn)
        left.addStretch()
        center = QVBoxLayout()
        center.setSpacing(6)
        controls = QHBoxLayout()
        controls.setAlignment(Qt.AlignCenter)
        controls.setSpacing(14)
        skip_btn_style = "QPushButton { background: transparent; border: none; border-radius: 14px; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.08); }"
        prev_btn = QPushButton()
        prev_btn.setFixedSize(28, 28)
        prev_btn.setCursor(Qt.PointingHandCursor)
        prev_btn.setStyleSheet(skip_btn_style)
        prev_btn.setIcon(self._make_prev_icon(18, "#d0d0d0"))
        prev_btn.setIconSize(QSize(18, 18))
        prev_btn.clicked.connect(self.play_previous_track)
        controls.addWidget(prev_btn)
        self.play_pause_btn = QPushButton()
        self.play_pause_btn.setFixedSize(36, 36)
        self.play_pause_btn.setCursor(Qt.PointingHandCursor)
        self.play_pause_btn.setStyleSheet("QPushButton { background-color: #ffffff; border: none; border-radius: 18px; } QPushButton:hover { background-color: #e6e6e6; }")
        self.play_pause_btn.setIcon(self._play_icon)
        self.play_pause_btn.setIconSize(QSize(16, 16))
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        controls.addWidget(self.play_pause_btn)
        next_btn = QPushButton()
        next_btn.setFixedSize(28, 28)
        next_btn.setCursor(Qt.PointingHandCursor)
        next_btn.setStyleSheet(skip_btn_style)
        next_btn.setIcon(self._make_next_icon(18, "#d0d0d0"))
        next_btn.setIconSize(QSize(18, 18))
        next_btn.clicked.connect(self.play_next_track)
        controls.addWidget(next_btn)
        progress = QHBoxLayout()
        self.time_now = QLabel("00:00")
        self.time_now.setStyleSheet("color: #888; font-size: 9px;")
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderPressed.connect(self._on_seek_pressed)
        self.progress_slider.sliderReleased.connect(self._on_seek_released)
        self.progress_slider.sliderMoved.connect(self._on_seek_moved)
        self.time_total = QLabel("00:00")
        self.time_total.setStyleSheet("color: #888; font-size: 9px;")
        progress.addWidget(self.time_now)
        progress.addWidget(self.progress_slider)
        progress.addWidget(self.time_total)
        center.addLayout(controls)
        center.addLayout(progress)
        right = QHBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(8)
        right.addStretch()
        self.vol_btn = QPushButton()
        self.vol_btn.setFixedSize(24, 24)
        self.vol_btn.setCursor(Qt.PointingHandCursor)
        self.vol_btn.setStyleSheet("background: transparent; border: none;")
        self.vol_btn.setIcon(self._vol_icon)
        self.vol_btn.setIconSize(QSize(16, 16))
        self.vol_btn.clicked.connect(self._toggle_mute)
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(100)
        self.vol_slider.setCursor(Qt.PointingHandCursor)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)
        right.addWidget(self.vol_btn)
        right.addWidget(self.vol_slider)
        layout.addLayout(left, 1)
        layout.addLayout(center, 2)
        layout.addLayout(right, 1)
        return player_bar


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow(username="TestUser")
    window.show()
    sys.exit(app.exec())