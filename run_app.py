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
        self.login_window.login_successful.connect(self.show_dashboard)

    def start(self):
        self.login_window.show()

    def show_dashboard(self):
        self.main_window = MainWindow()
        self.main_window.show()
        self.login_window.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    router = AppRouter()
    router.start()

    sys.exit(app.exec())