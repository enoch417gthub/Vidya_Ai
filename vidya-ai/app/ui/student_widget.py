# app/ui/student_widget.py
# ============================================================
# Student home dashboard -- personalized welcome screen
# Shows: XP level, study streak, daily challenge, quick nav
# ============================================================
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import httpx
import datetime

API_BASE = 'http://127.0.0.1:8000/api'


class StatCard(QFrame):
    '''A colored card widget showing a single stat (XP, streak, level)'''
    def __init__(self, title: str, value: str, color: str):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f'background:{color}; border-radius:8px; padding:10px;')

        layout = QVBoxLayout(self)

        val_label = QLabel(value)
        val_label.setFont(QFont('Calibri', 24, QFont.Weight.Bold))
        val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_label.setStyleSheet('color:white;')

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet('color:rgba(255,255,255,0.85); font-size:11px;')

        layout.addWidget(val_label)
        layout.addWidget(title_label)


class StudentWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.student_id = None  # Set after student logs in
        self.student_name = 'Student'
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # --- Welcome header ---
        self.welcome_label = QLabel('Welcome back, Student!')
        self.welcome_label.setFont(QFont('Calibri', 20, QFont.Weight.Bold))
        self.welcome_label.setStyleSheet('color: #1B3A5C;')
        layout.addWidget(self.welcome_label)

        # Date and time display
        self.date_label = QLabel()
        self.date_label.setStyleSheet('color: #7F8C8D; font-size:12px;')
        self._update_datetime()

        # Timer to update time every minute
        timer = QTimer(self)
        timer.timeout.connect(self._update_datetime)
        timer.start(60000)  # 60,000 ms = 1 minute
        layout.addWidget(self.date_label)

        # --- Stat cards row (XP, Level, Streak) ---
        stats_row = QHBoxLayout()
        self.xp_card = StatCard('Total XP', '0', '#2471A3')
        self.level_card = StatCard('Level', '1', '#1A7A40')
        self.streak_card = StatCard('Study Streak', '0 days', '#B7500A')
        stats_row.addWidget(self.xp_card)
        stats_row.addWidget(self.level_card)
        stats_row.addWidget(self.streak_card)
        layout.addLayout(stats_row)

        # --- Daily Challenge box ---
        challenge_group = QGroupBox('Daily Challenge')
        challenge_layout = QVBoxLayout()
        self.challenge_label = QLabel('Loading today\'s challenge...')
        self.challenge_label.setWordWrap(True)
        challenge_layout.addWidget(self.challenge_label)

        self.challenge_btn = QPushButton('Start Challenge (+50 XP)')
        self.challenge_btn.setStyleSheet('background:#F4D03F; color:#1B3A5C; font-weight:bold;')
        challenge_layout.addWidget(self.challenge_btn)

        challenge_group.setLayout(challenge_layout)
        layout.addWidget(challenge_group)

        # --- Quick Access buttons ---
        nav_group = QGroupBox('Quick Access')
        nav_grid = QGridLayout()
        buttons = [
            ('AI Tutor Chat', '#2471A3', (0, 0)),
            ('Generate Notes', '#1A7A40', (0, 1)),
            ('Exam Prep Mode', '#B7500A', (1, 0)),
            ('Flashcards', '#6C3483', (1, 1)),
        ]

        for label, color, (row, col) in buttons:
            btn = QPushButton(label)
            btn.setMinimumHeight(60)
            btn.setStyleSheet(f'background:{color}; color:white; border-radius:6px; font-size:13px; font-weight:bold;')
            nav_grid.addWidget(btn, row, col)

        nav_group.setLayout(nav_grid)
        layout.addWidget(nav_group)
        layout.addStretch()

    def _update_datetime(self):
        now = datetime.datetime.now()
        self.date_label.setText(now.strftime('%A, %d %B %Y | %I:%M %p'))

    def load_student_data(self, student_id: int):
        '''Fetch and display student stats from API'''
        self.student_id = student_id
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(f'{API_BASE}/student/{student_id}')
                data = r.json()

                self.student_name = data['name']
                self.welcome_label.setText(f'Welcome back, {data["name"]}!')

                # Update stat cards
                self.xp_card.findChild(QLabel).setText(str(data.get('xp_points', 0)))
                self.level_card.findChild(QLabel).setText(str(data.get('level', 1)))
                self.streak_card.findChild(QLabel).setText(f"{data.get('study_streak', 0)} days")

        except Exception as e:
            self.welcome_label.setText('Welcome to VIDYA AI!')