# app/ui/chat_widget.py
# ============================================================
# The main AI chat interface widget
# Sends questions to the FastAPI backend, displays streamed answers
# ============================================================
import httpx
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QLineEdit, QPushButton, QComboBox, QLabel, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

API_BASE = 'http://127.0.0.1:8000/api'


class AskWorker(QThread):
    '''
    Background thread for API calls — keeps UI responsive.
    Never make network/blocking calls on the main Qt thread.
    '''
    answer_ready = pyqtSignal(dict)  # Emitted when full answer arrives
    error_occurred = pyqtSignal(str)  # Emitted on error

    def __init__(self, question, grade, subject):
        super().__init__()
        self.question = question
        self.grade = grade
        self.subject = subject

    def run(self):
        '''Runs in background thread — calls the FastAPI /chat/ask endpoint'''
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f'{API_BASE}/chat/ask',
                    json={
                        'question': self.question,
                        'grade': self.grade,
                        'subject': self.subject
                    }
                )
                data = response.json()
                self.answer_ready.emit(data)  # Send result to UI thread
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChatWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Top bar: grade + subject selectors ---
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel('Grade:'))
        self.grade_combo = QComboBox()
        self.grade_combo.addItems(['grade_10', 'grade_11', 'grade_12'])
        top_bar.addWidget(self.grade_combo)

        top_bar.addWidget(QLabel('Subject:'))
        self.subject_combo = QComboBox()
        self.subject_combo.addItems(['physics', 'chemistry', 'mathematics', 'biology'])
        top_bar.addWidget(self.subject_combo)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # --- Main splitter: chat + citations panel ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Chat display area (HTML-capable for formatted answers)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont('Segoe UI', 11))
        splitter.addWidget(self.chat_display)

        # Source citations panel
        self.citations_panel = QTextEdit()
        self.citations_panel.setReadOnly(True)
        self.citations_panel.setMaximumWidth(280)
        self.citations_panel.setPlaceholderText('Source citations will appear here...')
        splitter.addWidget(self.citations_panel)
        splitter.setSizes([700, 280])  # Default split proportions
        layout.addWidget(splitter)

        # --- Bottom bar: input + send button ---
        bottom = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText('Ask your question here...')
        self.input_field.returnPressed.connect(self.send_question)  # Enter key sends
        bottom.addWidget(self.input_field)

        self.send_btn = QPushButton('Ask AI')
        self.send_btn.clicked.connect(self.send_question)
        self.send_btn.setFixedWidth(100)
        bottom.addWidget(self.send_btn)
        layout.addLayout(bottom)

    def send_question(self):
        question = self.input_field.text().strip()
        if not question:
            return

        grade = self.grade_combo.currentText()
        subject = self.subject_combo.currentText()

        # Display student's question in chat
        self.chat_display.append(f'<b style="color:#1B3A5C">You:</b> {question}<br>')
        self.input_field.clear()
        self.send_btn.setEnabled(False)  # Disable while AI is thinking
        self.chat_display.append('<i style="color:#888">VIDYA AI is thinking...</i>')

        # Spawn background worker thread to call API
        self.worker = AskWorker(question, grade, subject)
        self.worker.answer_ready.connect(self._on_answer)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

    def _on_answer(self, data: dict):
        '''Called when AI answer arrives — update chat display'''
        # Remove 'thinking...' placeholder
        cursor = self.chat_display.textCursor()
        self.chat_display.undo()  # Remove placeholder line

        answer = data.get('answer', 'No answer received.')
        self.chat_display.append(f'<b style="color:#1A7A40">VIDYA AI:</b><br>{answer}<br><hr>')

        # Show citations in the side panel
        sources = data.get('sources', [])
        if sources:
            citation_html = '<b>Sources Used:</b><br>'
            for s in sources:
                citation_html += f'<br><b>{s["source"]}</b> (p.{s["page"]})<br>'
                citation_html += f'<small><i>{s["excerpt"][:100]}...</i></small><br>'
            self.citations_panel.setHtml(citation_html)

        self.send_btn.setEnabled(True)  # Re-enable send button

    def _on_error(self, error_msg: str):
        self.chat_display.append(f'<span style="color:red">Error: {error_msg}</span><br>')
        self.send_btn.setEnabled(True)