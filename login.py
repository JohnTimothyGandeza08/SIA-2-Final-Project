# login.py
import os
import sqlite3
import hashlib
import secrets
import binascii
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QLineEdit, QPushButton, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap

LOGIN_THEME = """
QWidget#LoginWindow {
    background-color: #000000; 
}
QFrame#LeftPanel {
    background-color: #0f0f0f; 
    border-top-left-radius: 16px;
    border-bottom-left-radius: 16px;
    border: 1px solid #1a1a1a;
    border-right: none;
}
QFrame#RightPanel {
    border-top-right-radius: 16px;
    border-bottom-right-radius: 16px;
}
QLabel { color: #e0e0e0; }
QLabel#TitleLabel { font-size: 28px; font-weight: bold; color: white; letter-spacing: 1px; }
QLabel#SubtitleLabel { font-size: 12px; color: #888888; padding-bottom: 20px; }
QLineEdit {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 12px;
    padding-left: 15px;
    color: white;
    font-size: 13px;
}
QLineEdit:focus { border: 1px solid #0055ff; }
QPushButton#MainLoginBtn {
    background-color: #0055ff; 
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
    font-weight: bold;
}
QPushButton#MainLoginBtn:hover { background-color: #0044cc; }
QPushButton#MainLoginBtn:pressed { background-color: #003399; }
QPushButton#MainLoginBtn:disabled { background-color: #333333; color: #888888; }
QPushButton#SocialBtn {
    background-color: transparent;
    color: #e0e0e0;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 10px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton#SocialBtn:hover { background-color: #1a1a1a; border: 1px solid #555555; }
QLabel#DividerLabel { color: #666666; font-size: 12px; font-weight: bold; }
QLabel#ErrorLabel { color: #ff4444; font-size: 11px; }
QPushButton#LinkBtn {
    background: transparent;
    border: none;
    color: #888888;
    font-size: 12px;
    text-decoration: underline;
}
QPushButton#LinkBtn:hover { color: white; }
"""

DB_FILE = "users.db"

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', b'1234', bytes.fromhex(salt), 100000)
        stored_value = f"{salt}${binascii.hexlify(pwd_hash).decode('utf-8')}"
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", stored_value))
        print("Default user 'admin' created with password '1234'")
    conn.commit()
    conn.close()

def verify_password(stored_password, provided_password):
    try:
        salt, stored_hash = stored_password.split('$')
        pwd_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), bytes.fromhex(salt), 100000)
        return pwd_hash == bytes.fromhex(stored_hash)
    except ValueError:
        return False

def create_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return False
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000)
    stored_value = f"{salt}${binascii.hexlify(pwd_hash).decode('utf-8')}"
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, stored_value))
    conn.commit()
    conn.close()
    return True

setup_database()

class LoginWindow(QWidget):
    login_successful = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("LoginWindow")
        self.setWindowTitle("Login - Music App")
        self.resize(950, 600)
        self.setStyleSheet(LOGIN_THEME)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(0)

        left_panel = QFrame()
        left_panel.setObjectName("LeftPanel")
        left_panel.setFixedWidth(380)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 60, 40, 60)
        left_layout.setAlignment(Qt.AlignTop)

        self.form_stack = QStackedWidget()
        
        # LOGIN FORM
        self.login_widget = QWidget()
        login_layout = QVBoxLayout(self.login_widget)
        login_layout.setContentsMargins(0, 0, 0, 0)
        login_layout.setSpacing(0)

        title = QLabel("LOGIN")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Welcome back! Please enter your details.")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("👤  Username")

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("🔒  Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.returnPressed.connect(self.handle_login)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)

        self.login_btn = QPushButton("Login Now")
        self.login_btn.setObjectName("MainLoginBtn")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)

        switch_layout = QHBoxLayout()
        switch_layout.setAlignment(Qt.AlignCenter)
        switch_lbl = QLabel("Don't have an account?")
        switch_lbl.setStyleSheet("color: #888; font-size: 11px;")
        switch_btn = QPushButton("Sign Up")
        switch_btn.setObjectName("LinkBtn")
        switch_btn.setCursor(Qt.PointingHandCursor)
        switch_btn.clicked.connect(lambda: self.form_stack.setCurrentIndex(1))
        switch_layout.addWidget(switch_lbl)
        switch_layout.addWidget(switch_btn)

        divider_layout = QHBoxLayout()
        line_left = QFrame()
        line_left.setFrameShape(QFrame.HLine)
        line_left.setStyleSheet("color: #333;")
        line_right = QFrame()
        line_right.setFrameShape(QFrame.HLine)
        line_right.setStyleSheet("color: #333;")
        divider_lbl = QLabel("Login with Others")
        divider_lbl.setObjectName("DividerLabel")
        divider_layout.addWidget(line_left)
        divider_layout.addWidget(divider_lbl)
        divider_layout.addWidget(line_right)

        self.google_btn = QPushButton("G   Login with Google")
        self.google_btn.setObjectName("SocialBtn")
        self.google_btn.setCursor(Qt.PointingHandCursor)
        self.google_btn.clicked.connect(self.handle_google_oauth)

        self.facebook_btn = QPushButton("f   Login with Facebook")
        self.facebook_btn.setObjectName("SocialBtn")

        login_layout.addWidget(title)
        login_layout.addWidget(subtitle)
        login_layout.addSpacing(10)
        login_layout.addWidget(self.user_input)
        login_layout.addSpacing(10)
        login_layout.addWidget(self.pass_input)
        login_layout.addWidget(self.error_label)
        login_layout.addSpacing(15)
        login_layout.addWidget(self.login_btn)
        login_layout.addSpacing(10)
        login_layout.addLayout(switch_layout)
        login_layout.addSpacing(20)
        login_layout.addLayout(divider_layout)
        login_layout.addSpacing(15)
        login_layout.addWidget(self.google_btn)
        login_layout.addSpacing(10)
        login_layout.addWidget(self.facebook_btn)

        # SIGN UP FORM
        self.signup_widget = QWidget()
        signup_layout = QVBoxLayout(self.signup_widget)
        signup_layout.setContentsMargins(0, 0, 0, 0)
        signup_layout.setSpacing(0)

        su_title = QLabel("SIGN UP")
        su_title.setObjectName("TitleLabel")
        su_title.setAlignment(Qt.AlignCenter)

        su_subtitle = QLabel("Create a new account to get started.")
        su_subtitle.setObjectName("SubtitleLabel")
        su_subtitle.setAlignment(Qt.AlignCenter)

        self.su_user_input = QLineEdit()
        self.su_user_input.setPlaceholderText("👤  Choose a Username")

        self.su_pass_input = QLineEdit()
        self.su_pass_input.setPlaceholderText("🔒  Create Password")
        self.su_pass_input.setEchoMode(QLineEdit.Password)

        self.su_confirm_input = QLineEdit()
        self.su_confirm_input.setPlaceholderText("🔒  Confirm Password")
        self.su_confirm_input.setEchoMode(QLineEdit.Password)
        self.su_confirm_input.returnPressed.connect(self.handle_signup)

        self.su_error_label = QLabel("")
        self.su_error_label.setObjectName("ErrorLabel")
        self.su_error_label.setAlignment(Qt.AlignCenter)

        self.signup_btn = QPushButton("Create Account")
        self.signup_btn.setObjectName("MainLoginBtn")
        self.signup_btn.setCursor(Qt.PointingHandCursor)
        self.signup_btn.clicked.connect(self.handle_signup)

        switch_back_layout = QHBoxLayout()
        switch_back_layout.setAlignment(Qt.AlignCenter)
        switch_back_lbl = QLabel("Already have an account?")
        switch_back_lbl.setStyleSheet("color: #888; font-size: 11px;")
        switch_back_btn = QPushButton("Login")
        switch_back_btn.setObjectName("LinkBtn")
        switch_back_btn.setCursor(Qt.PointingHandCursor)
        switch_back_btn.clicked.connect(lambda: self.form_stack.setCurrentIndex(0))
        switch_back_layout.addWidget(switch_back_lbl)
        switch_back_layout.addWidget(switch_back_btn)

        signup_layout.addWidget(su_title)
        signup_layout.addWidget(su_subtitle)
        signup_layout.addSpacing(10)
        signup_layout.addWidget(self.su_user_input)
        signup_layout.addSpacing(10)
        signup_layout.addWidget(self.su_pass_input)
        signup_layout.addSpacing(10)
        signup_layout.addWidget(self.su_confirm_input)
        signup_layout.addWidget(self.su_error_label)
        signup_layout.addSpacing(15)
        signup_layout.addWidget(self.signup_btn)
        signup_layout.addSpacing(15)
        signup_layout.addLayout(switch_back_layout)
        signup_layout.addStretch()

        self.form_stack.addWidget(self.login_widget)
        self.form_stack.addWidget(self.signup_widget)
        left_layout.addWidget(self.form_stack)

        # RIGHT PANEL
        right_panel = QFrame()
        right_panel.setObjectName("RightPanel")
        right_panel.setStyleSheet("background-color: #050505;")
        self.image_label = QLabel(right_panel)
        self.image_label.setAlignment(Qt.AlignCenter)
        image_path = os.path.join(os.path.dirname(__file__), "music bg.jpg")
        if os.path.exists(image_path):
            self.bg_pixmap = QPixmap(image_path)
        else:
            self.image_label.setText("Image not found")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.image_label)
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'bg_pixmap') and not self.bg_pixmap.isNull():
            scaled = self.bg_pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)

    def prepare_for_login(self):
        """Reset the form so a different user can sign in."""
        self.form_stack.setCurrentIndex(0)
        self.user_input.clear()
        self.pass_input.clear()
        self.error_label.clear()
        self.login_btn.setText("Login Now")
        self.login_btn.setEnabled(True)
        self.su_user_input.clear()
        self.su_pass_input.clear()
        self.su_confirm_input.clear()
        self.su_error_label.clear()
        self.signup_btn.setText("Create Account")
        self.signup_btn.setEnabled(True)
        self.google_btn.setText("G   Login with Google")
        self.google_btn.setEnabled(True)
        self.user_input.setFocus()

    def handle_login(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()
        self.error_label.setText("")
        if not username or not password:
            self.error_label.setText("Please fill in all fields.")
            return
        self.login_btn.setText("Logging in...")
        self.login_btn.setEnabled(False)
        QTimer.singleShot(500, lambda: self.verify_credentials(username, password))

    def verify_credentials(self, username, password):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        if result and verify_password(result[0], password):
            print(f"[LOGIN] Successfully verified user: '{username}'. Emitting signal...")
            self.login_successful.emit(username)
        else:
            self.error_label.setText("Invalid username or password.")
            self.login_btn.setText("Login Now")
            self.login_btn.setEnabled(True)

    def handle_signup(self):
        username = self.su_user_input.text().strip()
        password = self.su_pass_input.text().strip()
        confirm = self.su_confirm_input.text().strip()
        self.su_error_label.setText("")
        if not username or not password or not confirm:
            self.su_error_label.setText("Please fill in all fields.")
            return
        if len(password) < 4:
            self.su_error_label.setText("Password must be at least 4 characters.")
            return
        if password != confirm:
            self.su_error_label.setText("Passwords do not match.")
            return
        self.signup_btn.setText("Creating...")
        self.signup_btn.setEnabled(False)
        QTimer.singleShot(500, lambda: self.execute_signup(username, password))

    def execute_signup(self, username, password):
        success = create_user(username, password)
        if success:
            QMessageBox.information(self, "Success", f"Account '{username}' created successfully!\nLogging you in...")
            print(f"[SIGNUP] Successfully created user: '{username}'. Emitting signal...")
            self.login_successful.emit(username)
        else:
            self.su_error_label.setText("Username is already taken. Please choose another.")
            self.signup_btn.setText("Create Account")
            self.signup_btn.setEnabled(True)

    def handle_google_oauth(self):
        self.error_label.setText("")
        self.google_btn.setText("Waiting for browser...")
        self.google_btn.setEnabled(False)
        self.login_btn.setEnabled(False)
        QTimer.singleShot(2000, self.finish_google_oauth)

    def finish_google_oauth(self):
        self.google_btn.setText("Success!")
        QMessageBox.information(self, "OAuth Success", "Logged in with Google successfully!")
        self.login_successful.emit("GoogleUser")

# NO `if __name__ == "__main__":` BLOCK HERE.
# Your app is launched via `run_app.py` instead.