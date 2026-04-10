# app/db/models.py
# ============================================================
# SQLAlchemy ORM models — defines all database tables
# Each class = one table in the SQLite database
# ============================================================
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Document(Base):
    '''Tracks every uploaded educational document'''
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)  # Original file name
    filepath = Column(String(512), nullable=False)  # Path to raw file
    subject = Column(String(100), nullable=False)  # e.g. 'physics'
    grade = Column(String(50), nullable=False)  # e.g. 'grade_10'
    doc_type = Column(String(50), default='notes')  # notes/textbook/question_paper
    chunk_count = Column(Integer, default=0)  # Number of text chunks indexed
    file_size = Column(Integer, default=0)  # File size in bytes
    indexed = Column(Boolean, default=False)  # Has been processed by indexer?
    indexed_at = Column(DateTime, nullable=True)  # When indexing completed
    created_at = Column(DateTime, default=datetime.utcnow)
    checksum = Column(String(64), nullable=True)  # MD5 hash to detect duplicates

    # Relationship: one document has many chunks
    chunks = relationship('Chunk', back_populates='document', cascade='all, delete')


class Chunk(Base):
    '''Individual text chunk extracted from a document'''
    __tablename__ = 'chunks'

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position in document (0,1,2...)
    content = Column(Text, nullable=False)  # The actual text content
    page_number = Column(Integer, nullable=True)  # Source PDF page number
    char_start = Column(Integer, nullable=True)  # Character offset start
    char_end = Column(Integer, nullable=True)  # Character offset end

    document = relationship('Document', back_populates='chunks')


class Student(Base):
    '''Student profile and preferences'''
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    grade = Column(String(50), nullable=False)  # e.g. 'grade_10'
    language_pref = Column(String(10), default='en')  # Preferred language code
    xp_points = Column(Integer, default=0)  # Gamification XP
    study_streak = Column(Integer, default=0)  # Consecutive study days
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, nullable=True)

    sessions = relationship('Session', back_populates='student')
    quiz_results = relationship('QuizResult', back_populates='student')


class Session(Base):
    '''A single study session (student opens app, studies, closes)'''
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject = Column(String(100), nullable=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    message_count = Column(Integer, default=0)

    student = relationship('Student', back_populates='sessions')
    messages = relationship('Message', back_populates='session')


class Message(Base):
    '''Individual chat messages within a session'''
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False)
    role = Column(String(10), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)  # Message text
    language = Column(String(10), default='en')  # Language of this message
    timestamp = Column(DateTime, default=datetime.utcnow)
    sources = Column(Text, nullable=True)  # JSON list of source citations

    session = relationship('Session', back_populates='messages')


class QuizResult(Base):
    '''Records of student quiz attempts'''
    __tablename__ = 'quiz_results'

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    subject = Column(String(100), nullable=False)
    score = Column(Integer, nullable=False)  # Correct answers
    total = Column(Integer, nullable=False)  # Total questions
    weak_topics = Column(Text, nullable=True)  # JSON list of weak areas
    taken_at = Column(DateTime, default=datetime.utcnow)

    student = relationship('Student', back_populates='quiz_results')