# run_app.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from login import LoginWindow
from dashboard import MainWindow

class AppRouter:
    """Handles the flow between the Login window and the Main Dashboard."""
    def __init__(self):
        self.login_window = LoginWindow()
        self.main_window = None
        self.login_window.login_successful.connect(self.show_dashboard)

    def start(self):
        self.login_window.show()

    def show_dashboard(self, username):
        self.main_window = MainWindow(username=username)
        self.main_window.logout_requested.connect(self.show_login)
        self.main_window.show()
        self.login_window.hide()

    def show_login(self):
        self.login_window.prepare_for_login()
        self.login_window.show()
        self.login_window.raise_()
        self.login_window.activateWindow()
        if self.main_window is not None:
            window = self.main_window
            self.main_window = None
            window.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    router = AppRouter()
    router.start()

    sys.exit(app.exec())