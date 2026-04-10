# app/db/crud.py
# ============================================================
# Database CRUD helper functions
# All database queries go here -- keeps API routes clean.
# Each function takes a 'db' Session and returns ORM objects.
# ============================================================
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from app.db.models import Document, Chunk, Student, Session as StudySession, Message, QuizResult


# ============================================================
# DOCUMENT CRUD
# ============================================================
def get_document(db: Session, doc_id: int) -> Optional[Document]:
    '''Fetch a document by its primary key ID'''
    return db.query(Document).filter(Document.id == doc_id).first()


def get_documents_by_subject(db: Session, grade: str, subject: str) -> List[Document]:
    '''List all documents for a specific grade/subject, newest first'''
    return db.query(Document).filter(
        Document.grade == grade,
        Document.subject == subject
    ).order_by(desc(Document.created_at)).all()


def get_document_by_checksum(db: Session, checksum: str) -> Optional[Document]:
    '''Check if a document with this MD5 checksum already exists (duplicate detection)'''
    return db.query(Document).filter(Document.checksum == checksum).first()


def mark_document_indexed(db: Session, doc_id: int, chunk_count: int) -> Document:
    '''Update document record after indexing completes'''
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        doc.chunk_count = chunk_count
        doc.indexed = True
        doc.indexed_at = datetime.utcnow()
        db.commit()
        db.refresh(doc)
    return doc


def delete_document(db: Session, doc_id: int) -> bool:
    '''Delete a document and all its chunks from the database'''
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        db.delete(doc)  # Cascade deletes chunks too (defined in model)
        db.commit()
        return True
    return False


def get_all_grades(db: Session) -> List[str]:
    '''Return distinct list of all grades that have documents'''
    rows = db.query(Document.grade).distinct().all()
    return [r[0] for r in rows]


# ============================================================
# STUDENT CRUD
# ============================================================
def get_student(db: Session, student_id: int) -> Optional[Student]:
    return db.query(Student).filter(Student.id == student_id).first()


def get_all_students(db: Session) -> List[Student]:
    '''Get all students -- used in teacher dashboard'''
    return db.query(Student).order_by(desc(Student.last_active)).all()


def update_student_activity(db: Session, student_id: int) -> None:
    '''Update last_active timestamp -- call at start of every session'''
    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        student.last_active = datetime.utcnow()
        db.commit()


# ============================================================
# SESSION & MESSAGE CRUD
# ============================================================
def create_session(db: Session, student_id: int, subject: str) -> StudySession:
    '''Start a new study session for a student'''
    session = StudySession(
        student_id=student_id,
        subject=subject,
        start_time=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def close_session(db: Session, session_id: int) -> None:
    '''Mark a session as ended when student closes chat or switches subject'''
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    if session:
        session.end_time = datetime.utcnow()
        db.commit()


def add_message(db: Session, session_id: int, role: str,
                content: str, language: str = 'en') -> Message:
    '''Save a chat message (user question or AI answer) to the database'''
    msg = Message(
        session_id=session_id,
        role=role,  # 'user' or 'assistant'
        content=content,
        language=language
    )
    db.add(msg)

    # Also increment the session message count
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    if session:
        session.message_count = (session.message_count or 0) + 1
    db.commit()
    return msg


# ============================================================
# QUIZ RESULT CRUD
# ============================================================
def save_quiz_result(
    db: Session, student_id: int, subject: str,
    score: int, total: int, weak_topics: list = None
) -> QuizResult:
    '''Save a quiz attempt result'''
    import json
    result = QuizResult(
        student_id=student_id,
        subject=subject,
        score=score,
        total=total,
        weak_topics=json.dumps(weak_topics or [])
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_student_quiz_stats(db: Session, student_id: int) -> dict:
    '''Aggregate quiz stats for a student -- used in teacher dashboard'''
    results = db.query(QuizResult).filter(
        QuizResult.student_id == student_id
    ).all()

    if not results:
        return {'total_quizzes': 0, 'avg_score': 0, 'best_subject': None}

    total = len(results)
    avg = sum(r.score / r.total * 100 for r in results if r.total > 0) / total

    by_subject = {}
    for r in results:
        by_subject.setdefault(r.subject, []).append(r.score / r.total if r.total else 0)

    best = max(by_subject, key=lambda s: sum(by_subject[s]) / len(by_subject[s]))

    return {'total_quizzes': total, 'avg_score': round(avg, 1), 'best_subject': best}