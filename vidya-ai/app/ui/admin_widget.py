# app/ui/admin_widget.py
# ============================================================
# Admin panel UI -- document management and upload interface
# Protected by admin password (entered in a dialog on first access)
# ============================================================
import os
import httpx
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QInputDialog, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

API_BASE = 'http://127.0.0.1:8000/api'


class UploadWorker(QThread):
    '''Background thread for file uploads -- keeps UI responsive during upload'''
    progress = pyqtSignal(str)  # Status message updates
    finished = pyqtSignal(dict)  # Upload result
    error = pyqtSignal(str)  # Error message

    def __init__(self, filepath, grade, subject, doc_type, admin_token):
        super().__init__()
        self.filepath = filepath
        self.grade = grade
        self.subject = subject
        self.doc_type = doc_type
        self.admin_token = admin_token

    def run(self):
        '''Send file to /api/upload/document via multipart POST'''
        try:
            self.progress.emit(f'Uploading {os.path.basename(self.filepath)}...')
            with open(self.filepath, 'rb') as f:
                with httpx.Client(timeout=300.0) as client:
                    response = client.post(
                        f'{API_BASE}/upload/document',
                        files={'file': (os.path.basename(self.filepath), f)},
                        data={
                            'grade': self.grade,
                            'subject': self.subject,
                            'doc_type': self.doc_type
                        },
                        headers={'X-Admin-Token': self.admin_token}  # Auth header
                    )
                    data = response.json()
                    self.progress.emit('Indexing in background -- please wait...')
                    self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class AdminWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.admin_token = None  # Set after password verification
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- Auth section ---
        auth_group = QGroupBox('Admin Authentication')
        auth_layout = QHBoxLayout()
        self.auth_label = QLabel('Not authenticated')
        self.auth_label.setStyleSheet('color: #E74C3C; font-weight: bold;')
        self.login_btn = QPushButton('Login as Admin')
        self.login_btn.clicked.connect(self._prompt_password)
        auth_layout.addWidget(self.auth_label)
        auth_layout.addStretch()
        auth_layout.addWidget(self.login_btn)
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)

        # --- Upload section ---
        upload_group = QGroupBox('Upload Educational Material')
        upload_layout = QVBoxLayout()

        # Grade + Subject + Doc type selectors
        selectors = QHBoxLayout()
        selectors.addWidget(QLabel('Grade:'))
        self.grade_combo = QComboBox()
        self.grade_combo.addItems(['grade_10', 'grade_11', 'grade_12', 'grade_9'])
        selectors.addWidget(self.grade_combo)

        selectors.addWidget(QLabel('Subject:'))
        self.subject_input = QComboBox()
        self.subject_input.setEditable(True)  # Allow custom subject names
        self.subject_input.addItems(['physics', 'chemistry', 'mathematics', 'biology', 'history'])
        selectors.addWidget(self.subject_input)

        selectors.addWidget(QLabel('Type:'))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['notes', 'textbook', 'question_paper', 'reference'])
        selectors.addWidget(self.type_combo)
        upload_layout.addLayout(selectors)

        # File picker button
        file_row = QHBoxLayout()
        self.file_label = QLabel('No file selected')
        self.file_label.setStyleSheet('color: #7F8C8D;')
        self.pick_btn = QPushButton('Choose File (PDF/PPT/DOCX)')
        self.pick_btn.clicked.connect(self._pick_file)
        self.upload_btn = QPushButton('Upload & Index')
        self.upload_btn.clicked.connect(self._upload_file)
        self.upload_btn.setEnabled(False)  # Disabled until file is chosen
        file_row.addWidget(self.file_label)
        file_row.addWidget(self.pick_btn)
        file_row.addWidget(self.upload_btn)
        upload_layout.addLayout(file_row)

        # Progress bar (shown during upload)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate spinner mode
        self.progress_bar.hide()  # Hidden until upload starts
        upload_layout.addWidget(self.progress_bar)

        self.status_label = QLabel('')
        upload_layout.addWidget(self.status_label)

        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)

        # --- Indexed documents table ---
        docs_group = QGroupBox('Indexed Documents')
        docs_layout = QVBoxLayout()
        self.docs_table = QTableWidget(0, 5)  # 5 columns
        self.docs_table.setHorizontalHeaderLabels(['Filename', 'Grade', 'Subject', 'Chunks', 'Indexed'])
        self.docs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.docs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        docs_layout.addWidget(self.docs_table)

        refresh_btn = QPushButton('Refresh List')
        refresh_btn.clicked.connect(self._load_documents)
        docs_layout.addWidget(refresh_btn)

        docs_group.setLayout(docs_layout)
        layout.addWidget(docs_group)

        self._selected_file = None

    def _prompt_password(self):
        '''Show password dialog for admin login'''
        pw, ok = QInputDialog.getText(self, 'Admin Login', 'Enter admin password:',
                                       flags=Qt.WindowType.Dialog)
        if ok and pw:
            self.admin_token = pw
            self.auth_label.setText('Authenticated as Admin')
            self.auth_label.setStyleSheet('color: #27AE60; font-weight: bold;')
            self._load_documents()  # Load document list after login

    def _pick_file(self):
        '''Open file picker dialog'''
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Document', '',
            'Documents (*.pdf *.pptx *.docx *.txt)'
        )
        if path:
            self._selected_file = path
            self.file_label.setText(os.path.basename(path))
            self.upload_btn.setEnabled(True)

    def _upload_file(self):
        '''Start background upload'''
        if not self.admin_token:
            QMessageBox.warning(self, 'Auth Required', 'Please login as admin first.')
            return
        if not self._selected_file:
            return

        self.progress_bar.show()
        self.upload_btn.setEnabled(False)

        self.worker = UploadWorker(
            self._selected_file,
            self.grade_combo.currentText(),
            self.subject_input.currentText(),
            self.type_combo.currentText(),
            self.admin_token
        )
        self.worker.progress.connect(lambda msg: self.status_label.setText(msg))
        self.worker.finished.connect(self._on_upload_done)
        self.worker.error.connect(self._on_upload_error)
        self.worker.start()

    def _on_upload_done(self, data: dict):
        self.progress_bar.hide()
        self.upload_btn.setEnabled(True)
        self.status_label.setText(f'Upload complete: {data.get("filename", "")} (Doc ID: {data.get("doc_id")})')
        self._load_documents()  # Refresh the table

    def _on_upload_error(self, error: str):
        self.progress_bar.hide()
        self.upload_btn.setEnabled(True)
        self.status_label.setText(f'Error: {error}')
        QMessageBox.critical(self, 'Upload Error', error)

    def _load_documents(self):
        '''Fetch and display all indexed documents from the API'''
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(f'{API_BASE}/upload/documents',
                               headers={'X-Admin-Token': self.admin_token or ''})
                docs = r.json().get('documents', [])

                self.docs_table.setRowCount(len(docs))
                for i, doc in enumerate(docs):
                    self.docs_table.setItem(i, 0, QTableWidgetItem(doc.get('filename', '')))
                    self.docs_table.setItem(i, 1, QTableWidgetItem(doc.get('grade', '')))
                    self.docs_table.setItem(i, 2, QTableWidgetItem(doc.get('subject', '')))
                    self.docs_table.setItem(i, 3, QTableWidgetItem(str(doc.get('chunk_count', 0))))
                    self.docs_table.setItem(i, 4, QTableWidgetItem('Yes' if doc.get('indexed') else 'Pending'))
        except Exception as e:
            self.status_label.setText(f'Could not load documents: {e}')