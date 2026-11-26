# dashboard.py
import sys
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QSlider, QGridLayout, QStackedWidget
)
from PySide6.QtCore import Qt, QPointF, QUrl, QThread, Signal, QByteArray, QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPixmap, QImage, QIcon, QPen
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from theme import DARK_THEME
import jamendo_api


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
            self.query,
            artist_limit=6,
            artist_tracks_limit=6,
            track_limit=20,
        )

        # Pre-fetch raw image bytes off the GUI thread (QPixmap conversion stays on main thread)
        urls = set()
        for artist in results.get("artists", []):
            if artist.get("image"):
                urls.add(artist["image"])
            for t in artist.get("tracks", []):
                img = t.get("album_image") or t.get("image")
                if img:
                    urls.add(img)
        for t in results.get("tracks", []):
            img = t.get("album_image") or t.get("image")
            if img:
                urls.add(img)

        image_bytes = {}
        url_list = list(urls)
        if url_list:
            with ThreadPoolExecutor(max_workers=8) as pool:
                fetched = list(pool.map(jamendo_api.download_image_bytes, url_list))
            for url, raw in zip(url_list, fetched):
                if raw:
                    image_bytes[url] = raw

        self.finished_search.emit(self.request_id, self.query, results, image_bytes)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pulse")
        self.resize(1100, 800)
        self.setStyleSheet(DARK_THEME)

        # Setup Media Player
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
        self.search_debounce_timer.timeout.connect(
            lambda: self.run_search(self.big_search.text())
        )

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

        # --- 1. TOP HEADER ---
        header = QWidget()
        header.setObjectName("TopHeader")
        header.setFixedHeight(64)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(30, 0, 30, 0)

        # Left: Logo
        logo_box = QHBoxLayout()
        logo_icon = QLabel("▶")
        logo_icon.setStyleSheet("background: #0055ff; color: white; border-radius: 4px; padding: 2px 6px; font-size: 12px;")
        logo_text = QLabel("Pulse")
        logo_text.setStyleSheet("color: white; font-weight: bold; font-size: 16px; margin-left: 5px;")
        logo_box.addWidget(logo_icon)
        logo_box.addWidget(logo_text)

        # Center: Segmented Control
        seg_widget = QWidget()
        seg_widget.setObjectName("SegmentedControl")
        seg_widget.setFixedSize(240, 34)

        seg_layout = QHBoxLayout(seg_widget)
        seg_layout.setContentsMargins(4, 4, 4, 4)
        seg_layout.setSpacing(0)

        for i, text in enumerate(["Music", "Video", "Games"]):
            btn = QPushButton(text)
            btn.setObjectName("SegBtnActive" if i == 0 else "SegBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedWidth(77)
            seg_layout.addWidget(btn)

        # Right: Search + Profile
        self.header_search = QLineEdit()
        self.header_search.setObjectName("SearchBar")
        self.header_search.setPlaceholderText("🔍 Search artists or songs...")
        self.header_search.setFixedSize(240, 30)
        self.header_search.returnPressed.connect(self._on_header_search)

        profile = QLabel("J")
        profile.setFixedSize(30, 30)
        profile.setAlignment(Qt.AlignCenter)
        profile.setStyleSheet("background: white; color: black; border-radius: 15px; font-weight: bold; font-size: 12px;")

        h_layout.addLayout(logo_box)
        h_layout.addStretch()
        h_layout.addWidget(seg_widget)
        h_layout.addStretch()
        h_layout.addWidget(self.header_search)
        h_layout.addWidget(profile)

        # --- 2. NAVBAR ---
        navbar = QWidget()
        navbar.setObjectName("TopNavBar")
        navbar.setFixedHeight(56)
        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(30, 0, 30, 0)
        nav_layout.setSpacing(15)

        self.nav_buttons = []
        nav_items = [("🏠  Home", 0), ("🔍  Search", 1), ("📚  Your Library", 2)]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("NavTopBtnActive" if index == 0 else "NavTopBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=index: self.set_page(i))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()

        # --- 3. STACKED WIDGET ---
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.build_home_page())      # Index 0
        self.stacked_widget.addWidget(self.build_search_page())    # Index 1
        self.stacked_widget.addWidget(self.build_library_page())   # Index 2

        # --- 4. ASSEMBLE ---
        outer_layout.addWidget(header)
        outer_layout.addWidget(navbar)
        outer_layout.addWidget(self.stacked_widget, 1)
        outer_layout.addWidget(self.create_player_bar())

    # ==========================================
    # VECTOR PLAYER ICONS (2x HiDPI)
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
        tri = QPolygonF([
            QPointF(size - margin, margin),
            QPointF(margin + bar_w + 1, size * 0.5),
            QPointF(size - margin, size - margin),
        ])
        p.drawPolygon(tri)
        p.end()
        return QIcon(pixmap)

    def _make_next_icon(self, size=18, color="#b3b3b3"):
        pixmap, p = self._new_icon_canvas(size)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(color)))
        bar_w = size * 0.12
        margin = size * 0.18
        tri = QPolygonF([
            QPointF(margin, margin),
            QPointF(size - margin - bar_w - 1, size * 0.5),
            QPointF(margin, size - margin),
        ])
        p.drawPolygon(tri)
        p.drawRect(int(size - margin - bar_w), int(margin), max(2, int(bar_w)), int(size - 2 * margin))
        p.end()
        return QIcon(pixmap)

    def _make_play_icon(self, size=16, color="#000000"):
        pixmap, p = self._new_icon_canvas(size)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(color)))
        tri = QPolygonF([
            QPointF(size * 0.28, size * 0.16),
            QPointF(size * 0.84, size * 0.5),
            QPointF(size * 0.28, size * 0.84),
        ])
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

        # Speaker body
        speaker = QPolygonF([
            QPointF(2.0, 6.0),
            QPointF(5.0, 6.0),
            QPointF(8.5, 3.0),
            QPointF(8.5, 13.0),
            QPointF(5.0, 10.0),
            QPointF(2.0, 10.0),
        ])
        p.drawPolygon(speaker)

        if muted:
            p.drawLine(QPointF(11.0, 5.5), QPointF(14.5, 10.5))
            p.drawLine(QPointF(14.5, 5.5), QPointF(11.0, 10.5))
        else:
            p.drawArc(7, 4, 5, 8, -55 * 16, 110 * 16)
            p.drawArc(7, 2, 8, 12, -55 * 16, 110 * 16)

        p.end()
        return QIcon(pixmap)

    def set_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setObjectName("NavTopBtnActive" if i == index else "NavTopBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _pixmap_from_url(self, url, width, height):
        if not url:
            return None
        pixmap = self._pixmap_cache.get(url)
        if pixmap is None:
            pixmap = jamendo_api.download_image(url)
            if pixmap:
                self._pixmap_cache[url] = pixmap
        if pixmap:
            return pixmap.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        return None

    def _track_key(self, track):
        return track.get("audio") or str(track.get("id") or "")

    def _is_liked(self, track):
        key = self._track_key(track)
        return bool(key) and any(self._track_key(t) == key for t in self.liked_tracks)

    def _apply_heart_style(self, btn, liked):
        btn.setText("♥" if liked else "♡")
        btn.setStyleSheet(
            "background: transparent; border: none; color: #ff5555; font-size: 14px;"
            if liked
            else "background: transparent; border: none; color: #888; font-size: 14px;"
        )

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
        if not track:
            return
        key = self._track_key(track)
        if not key:
            return

        existing_idx = next((i for i, t in enumerate(self.liked_tracks) if self._track_key(t) == key), None)
        if existing_idx is not None:
            self.liked_tracks.pop(existing_idx)
        else:
            self.liked_tracks.insert(0, dict(track))

        self._sync_heart_buttons()
        self._refresh_library_liked_songs()

    def _record_recently_played(self, track):
        key = self._track_key(track)
        if not key:
            return
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
        self.play_jamendo_track(
            audio_url,
            track_name,
            artist_name,
            duration_sec=duration_sec,
            img_url=img_url,
            track_obj=track,
        )

    def play_jamendo_track(self, audio_url, track_name, artist_name, duration_sec=0, img_url=None, track_obj=None):
        if not audio_url or not audio_url.startswith("http"):
            print(f"[PLAYER ERROR] Invalid audio URL: {audio_url}")
            return

        same_track = self.current_audio_url == audio_url
        if same_track and self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            return

        if not same_track:
            print(f"Playing: {track_name} from {audio_url}")
            self.current_audio_url = audio_url
            if track_obj is not None:
                self.current_track = dict(track_obj)
            else:
                self.current_track = {
                    "audio": audio_url,
                    "name": track_name,
                    "artist_name": artist_name,
                    "duration": duration_sec,
                    "album_image": img_url,
                }

            self.player_title.setText(track_name)
            self.player_artist.setText(artist_name or "Unknown Artist")

            scaled_art = self._pixmap_from_url(img_url, 50, 50)
            if scaled_art:
                self.player_art.setPixmap(scaled_art)
            else:
                self.player_art.clear()

            # Sync song bar immediately with the track's known duration
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
        if not self.current_playlist:
            return
        if self.media_player.position() > 3000:
            self.media_player.setPosition(0)
            return
        if self.current_index > 0:
            new_idx = self.current_index - 1
            self.play_track(self.current_playlist[new_idx], self.current_playlist, new_idx)

    def play_next_track(self):
        if not self.current_playlist:
            return
        if self.current_index + 1 < len(self.current_playlist):
            new_idx = self.current_index + 1
            self.play_track(self.current_playlist[new_idx], self.current_playlist, new_idx)

    def toggle_play_pause(self):
        if not self.current_audio_url:
            return
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _refresh_play_buttons(self, playing):
        if hasattr(self, "play_pause_btn"):
            self.play_pause_btn.setIcon(self._pause_icon if playing else self._play_icon)
        for btn, url in self.home_play_buttons + self.search_play_buttons + self.library_play_buttons:
            btn.setText("⏸" if playing and url == self.current_audio_url else "▶")

    def _on_playback_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._refresh_play_buttons(playing)

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next_track()

    def _format_time(self, ms):
        seconds = max(0, int(ms // 1000))
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _on_position_changed(self, position):
        if self._seeking or not hasattr(self, "progress_slider"):
            return
        if position > self.progress_slider.maximum():
            self.progress_slider.setMaximum(position)
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(position)
        self.progress_slider.blockSignals(False)
        self.time_now.setText(self._format_time(position))

    def _on_duration_changed(self, duration):
        if not hasattr(self, "progress_slider"):
            return
        effective_duration = duration if duration > 0 else self._expected_duration_ms
        self.progress_slider.setMaximum(max(effective_duration, 0))
        self.time_total.setText(self._format_time(effective_duration))

        if duration > 0:
            formatted = self._format_time(duration)
            for lbl, url in self.home_duration_labels + self.search_duration_labels + self.library_duration_labels:
                if url == self.current_audio_url:
                    lbl.setText(formatted)

    def _on_seek_pressed(self):
        self._seeking = True

    def _on_seek_released(self):
        self._seeking = False
        self.media_player.setPosition(self.progress_slider.value())

    def _on_seek_moved(self, value):
        self.time_now.setText(self._format_time(value))

    def _on_volume_changed(self, value):
        self.audio_output.setVolume(value / 100)
        if value > 0:
            self._last_volume = value
        if hasattr(self, "vol_btn"):
            self.vol_btn.setIcon(self._vol_muted_icon if value == 0 else self._vol_icon)

    def _toggle_mute(self):
        if self.vol_slider.value() > 0:
            self._last_volume = self.vol_slider.value()
            self.vol_slider.setValue(0)
        else:
            self.vol_slider.setValue(self._last_volume or 80)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

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

        # --- HERO BANNER ---
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

        # --- JUMP BACK IN ---
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
        recents = [
            ("Nils Frahm Radio", "Artist Mix"),
            ("Deep Focus Playlist", "42 tracks · Ambient"),
            ("All Melody", "Nils Frahm"),
            ("remember", "Ólafur Arnalds"),
            ("Eusa", "Hania Rani"),
            ("Singularity", "Jon Hopkins"),
        ]
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

        # --- LIVE JAMENDO TRACKS ---
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

                # Album Art
                art_label = QLabel()
                art_label.setFixedSize(84, 84)
                art_label.setStyleSheet("background-color: #333; border-radius: 6px;")

                img_url = track.get("album_image") or track.get("image")
                pixmap = self._pixmap_from_url(img_url, 84, 84)
                if pixmap:
                    art_label.setPixmap(pixmap)

                # Text Info
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

                # Action buttons (Like + Play)
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
                    play_btn.clicked.connect(
                        lambda checked, tr=track, pl=tracks, i=idx: self.play_track(tr, pl, i)
                    )

                actions_col.addWidget(heart_btn, alignment=Qt.AlignRight)
                actions_col.addStretch()
                actions_col.addWidget(play_btn, alignment=Qt.AlignRight)

                c_layout.addWidget(art_label)
                c_layout.addSpacing(8)
                c_layout.addLayout(text_col, 1)
                c_layout.addLayout(actions_col)

                mf_grid.addWidget(card, idx // 4, idx % 4)

            for col in range(4):
                mf_grid.setColumnStretch(col, 1)
            layout.addLayout(mf_grid)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

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

        # Search input row
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

        # Filter tabs
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

        # Search History section
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

        # Dynamic results container
        self.search_results_layout = QVBoxLayout()
        self.search_results_layout.setSpacing(16)
        layout.addLayout(self.search_results_layout)

        # Explorations
        explore_lbl = QLabel("EXPLORATIONS")
        explore_lbl.setObjectName("SectionTitle")
        layout.addWidget(explore_lbl)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        explorations = [
            ("Ambient", "Deep focus"),
            ("Classical", "Piano & strings"),
            ("Lo-Fi", "Quiet beats"),
            ("Electronic", "Synth & pulse"),
        ]
        for i, (title, sub) in enumerate(explorations):
            card = ClickableFrame()
            card.setObjectName("TableContainer")
            card.setFixedHeight(90)
            card.setCursor(Qt.PointingHandCursor)
            card.clicked.connect(lambda q=title: self._quick_search(q))
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 15, 15, 15)
            c_title = QLabel(title)
            c_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
            c_sub = QLabel(sub)
            c_sub.setStyleSheet("color: #888; font-size: 10px;")
            c_layout.addWidget(c_title)
            c_layout.addStretch()
            c_layout.addWidget(c_sub)
            grid_layout.addWidget(card, i // 4, i % 4)

        layout.addLayout(grid_layout)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _on_header_search(self):
        query = self.header_search.text().strip()
        if not query:
            return
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
        if not clean:
            return
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
            chip.setStyleSheet(
                "background-color: #1a1a1a; color: #ddd; border: 1px solid #333; "
                "border-radius: 14px; padding: 4px 12px; font-size: 11px;"
            )
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
        if request_id != self._search_request_id:
            return

        # Convert downloaded image bytes to QPixmap on the GUI thread
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

        # --- ARTISTS + THEIR SONGS ---
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
                if pixmap:
                    art_img.setPixmap(pixmap)

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
                main_play_btn.setStyleSheet(
                    "QPushButton { background-color: #ffffff; border: none; border-radius: 22px; }"
                    "QPushButton:hover { background-color: #e6e6e6; }"
                    "QPushButton:disabled { background-color: #333333; }"
                )
                main_play_btn.setIcon(self._make_play_icon(18, "#000000"))
                main_play_btn.setIconSize(QSize(18, 18))
                if artist_tracks:
                    main_play_btn.clicked.connect(
                        lambda checked, tr=artist_tracks[0], pl=artist_tracks: self.play_track(tr, pl, 0)
                    )
                else:
                    main_play_btn.setEnabled(False)

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
                            t_play.clicked.connect(
                                lambda checked, item=tr, pl=artist_tracks, i=idx: self.play_track(item, pl, i)
                            )

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

        # --- SONGS LIST ---
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
                row = self._build_song_row(
                    tr,
                    tracks,
                    idx,
                    self.search_play_buttons,
                    self.search_duration_labels,
                    self.search_heart_buttons,
                )
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
        if pixmap:
            thumb.setPixmap(pixmap)

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
            play_btn.clicked.connect(
                lambda checked, item=tr, pl=playlist, i=idx: self.play_track(item, pl, i)
            )

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

        # --- LIKED SONGS SECTION ---
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
        self.liked_banner_play_btn.setStyleSheet(
            "QPushButton { background-color: white; border: none; border-radius: 20px; }"
            "QPushButton:hover { background-color: #e6e6e6; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
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

        # --- RECENTLY PLAYED SECTION ---
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
        if self.liked_tracks:
            self.play_track(self.liked_tracks[0], self.liked_tracks, 0)

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
        self.liked_banner_sub.setText(
            f"{count} liked song{'s' if count != 1 else ''} · Latest: {latest.get('name', '')} by {latest.get('artist_name', '')}"
        )
        self.liked_banner_play_btn.setEnabled(True)

        table = QFrame()
        table.setObjectName("TableContainer")
        t_layout = QVBoxLayout(table)
        t_layout.setContentsMargins(16, 12, 16, 12)
        t_layout.setSpacing(6)

        for idx, tr in enumerate(self.liked_tracks):
            row = self._build_song_row(
                tr,
                self.liked_tracks,
                idx,
                self.library_play_buttons,
                self.library_duration_labels,
                self.library_heart_buttons,
            )
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
            if pixmap:
                art.setPixmap(pixmap)

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

        for col in range(4):
            grid.setColumnStretch(col, 1)
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

        # Pre-build crisp vector icons
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

        skip_btn_style = (
            "QPushButton { background: transparent; border: none; border-radius: 14px; }"
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.08); }"
        )

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
        self.play_pause_btn.setStyleSheet(
            "QPushButton { background-color: #ffffff; border: none; border-radius: 18px; }"
            "QPushButton:hover { background-color: #e6e6e6; }"
        )
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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())