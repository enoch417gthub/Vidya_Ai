# app/ui/main_window.py
# ============================================================
# Main application window — the root PyQt6 window
# Contains a tab widget switching between Student and Admin views
# ============================================================
import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QTabWidget, QStatusBar, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from app.ui.chat_widget import ChatWidget
from app.ui.admin_widget import AdminWidget
from app.ui.student_widget import StudentWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('VIDYA AI — Offline Tutor')
        self.setMinimumSize(1024, 720)  # Minimum window size

        # Apply the global Qt stylesheet (dark/light theme)
        with open('app/ui/styles.qss', 'r') as f:
            self.setStyleSheet(f.read())

        # Create tab container
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Add tabs
        self.student_tab = StudentWidget()  # Student home dashboard
        self.chat_tab = ChatWidget()        # AI chat interface
        self.admin_tab = AdminWidget()      # Admin upload panel

        self.tabs.addTab(self.student_tab, 'Home')
        self.tabs.addTab(self.chat_tab, 'AI Tutor')
        self.tabs.addTab(self.admin_tab, 'Admin')

        # Status bar at the bottom of the window
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage('VIDYA AI ready. Internet not required.')

        self.setCentralWidget(self.tabs)