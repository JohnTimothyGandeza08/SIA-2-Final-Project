# login.py
import os
import sqlite3
import hashlib
import secrets
import binascii
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
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
QLabel { 
color: #e0e0e0; 
}

QLabel#TitleLabel { 
font-size: 28px; 
font-weight: bold; 
color: white; 
letter-spacing: 1px; 
}

QLabel#SubtitleLabel { 
font-size: 12px; 
color: #888888; 
padding-bottom: 20px; 
}

QLineEdit {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 12px;
    padding-left: 15px;
    color: white;
    font-size: 13px;
}

QLineEdit:focus { 
border: 1px solid #0055ff; 
}

QPushButton#MainLoginBtn {
    background-color: #0055ff; 
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 14px;
    font-weight: bold;
}

QPushButton#MainLoginBtn:hover { 
background-color: #0044cc; 
}

QPushButton#MainLoginBtn:pressed { 
background-color: #003399; 
}

QPushButton#MainLoginBtn:disabled { 
background-color: #333333; 
color: #888888; 
}

QPushButton#SocialBtn {
    background-color: transparent;
    color: #e0e0e0;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 10px;
    font-size: 12px;
    font-weight: bold;
}
QPushButton#SocialBtn:hover {
    background-color: #1a1a1a;
    border: 1px solid #555555;
}

QPushButton#SocialBtn:disabled { 
color: #555555; 
border: 1px solid #222222; 
}

QLabel#DividerLabel { 
color: #666666; 
font-size: 12px; 
font-weight: bold; 
}

QLabel#ErrorLabel { 
color: #ff4444; font-size: 11px; 
}
"""

# ==========================================
# DATABASE & HASHING HELPERS
# ==========================================
DB_FILE = "users.db"

def setup_database():
    """Creates the SQLite database and a default user if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')
    
    # Create a default admin user for testing if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        # Hashing "1234" securely with a salt
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', b'1234', bytes.fromhex(salt), 100000)
        # Store salt and hash together (format: salt$hash)
        stored_value = f"{salt}${binascii.hexlify(pwd_hash).decode('utf-8')}"
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", stored_value))
        print("Default user 'admin' created with password '1234'")
        
    conn.commit()
    conn.close()

def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user"""
    try:
        salt, stored_hash = stored_password.split('$')
        pwd_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), bytes.fromhex(salt), 100000)
        return pwd_hash == bytes.fromhex(stored_hash)
    except ValueError:
        return False

# Initialize DB on startup
setup_database()

# ==========================================
# GUI CLASS
# ==========================================
class LoginWindow(QWidget):
    # Signal now passes the username string
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

        # LEFT PANEL (The Form)
        left_panel = QFrame()
        left_panel.setObjectName("LeftPanel")
        left_panel.setFixedWidth(380)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 60, 40, 60)
        left_layout.setAlignment(Qt.AlignTop)

        title = QLabel("LOGIN")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("How to get started lorem ipsum dolor at?")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("👤  Username")

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("🔒  Password")
        self.pass_input.setEchoMode(QLineEdit.Password)
        
        # Allow pressing Enter to login
        self.pass_input.returnPressed.connect(self.handle_login)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)

        self.login_btn = QPushButton("Login Now")
        self.login_btn.setObjectName("MainLoginBtn")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)

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

        # OAuth Google Button
        self.google_btn = QPushButton("G   Login with Google")
        self.google_btn.setObjectName("SocialBtn")
        self.google_btn.setCursor(Qt.PointingHandCursor)
        self.google_btn.clicked.connect(self.handle_google_oauth)

        self.facebook_btn = QPushButton("f   Login with Facebook")
        self.facebook_btn.setObjectName("SocialBtn")

        left_layout.addWidget(title)
        left_layout.addWidget(subtitle)
        left_layout.addSpacing(10)
        left_layout.addWidget(self.user_input)
        left_layout.addSpacing(10)
        left_layout.addWidget(self.pass_input)
        left_layout.addWidget(self.error_label)
        left_layout.addSpacing(15)
        left_layout.addWidget(self.login_btn)
        left_layout.addSpacing(20)
        left_layout.addLayout(divider_layout)
        left_layout.addSpacing(15)
        left_layout.addWidget(self.google_btn)
        left_layout.addSpacing(10)
        left_layout.addWidget(self.facebook_btn)

        # ==========================================
        # RIGHT PANEL (The Image)
        # ==========================================
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

    # ==========================================
    # MANUAL LOGIN LOGIC
    # ==========================================
    def handle_login(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text().strip()

        self.error_label.setText("")

        if not username or not password:
            self.error_label.setText("Please fill in all fields.")
            return

        self.login_btn.setText("Logging in...")
        self.login_btn.setEnabled(False)

        # Small delay for UI feedback
        QTimer.singleShot(500, lambda: self.verify_credentials(username, password))

    def verify_credentials(self, username, password):
        """Checks the SQLite database for the user and verifies the hash."""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        # Check if user exists and password hash matches
        if result and verify_password(result[0], password):
            self.login_successful.emit(username) # Emit the username
        else:
            self.error_label.setText("Invalid username or password.")
            self.login_btn.setText("Login Now")
            self.login_btn.setEnabled(True)

    # ==========================================
    # REAL OAUTH 2.0 SIMULATION
    # ==========================================
    def handle_google_oauth(self):
        """Simulates the real Google OAuth 2.0 flow."""
        self.error_label.setText("")
        self.google_btn.setText("Waiting for browser...")
        self.google_btn.setEnabled(False)
        self.login_btn.setEnabled(False)

        QTimer.singleShot(2000, self.finish_google_oauth)

    def finish_google_oauth(self):
        """Runs after the simulated browser login is done."""
        self.google_btn.setText("Success!")
        QMessageBox.information(self, "OAuth Success", "Logged in with Google successfully!")
        # For OAuth, we pass a generic name or a name from the OAuth provider
        self.login_successful.emit("GoogleUser")


# ==========================================
# ENTRY POINT
# ==========================================
if __name__ == "__main__":
    from dashboard import MainWindow
    
    app = QApplication(sys.argv)
    
    login_window = LoginWindow()
    dashboard_window = None # Keep reference to prevent garbage collection

    def on_login_success(username):
        global dashboard_window
        print(f"Login successful for: {username}")
        dashboard_window = MainWindow(username=username)
        dashboard_window.show()
        login_window.close()

    login_window.login_successful.connect(on_login_success)
    login_window.show()
    
    sys.exit(app.exec())