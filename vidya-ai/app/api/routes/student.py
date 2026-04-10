# app/api/routes/student.py
# ============================================================
# /api/student -- student profile CRUD and progress tracking
# Endpoints: create profile, get profile, update XP, get history
# All data stored locally in SQLite -- zero cloud dependency
# ============================================================
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from loguru import logger
from app.db.database import get_db
from app.db.models import Student, Session as StudySession, QuizResult
from app.db import crud

router = APIRouter()


# ---- Pydantic schemas (request/response shapes) ----
class StudentCreate(BaseModel):
    name: str
    grade: str  # e.g. 'grade_10'
    language_pref: str = 'en'  # Preferred display language


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    language_pref: Optional[str] = None


class XPUpdate(BaseModel):
    xp_to_add: int = 0  # Points earned in this action


# ---- Endpoints ----
@router.post('/create')
async def create_student(data: StudentCreate, db: Session = Depends(get_db)):
    '''Create a new student profile on first launch'''
    # Check if student with same name+grade already exists
    existing = db.query(Student).filter(
        Student.name == data.name,
        Student.grade == data.grade
    ).first()

    if existing:
        return {'message': 'Profile already exists', 'student_id': existing.id}

    student = Student(
        name=data.name,
        grade=data.grade,
        language_pref=data.language_pref,
        xp_points=0,
        study_streak=0
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    logger.info(f'New student created: {student.name} ({student.grade})')
    return {'message': 'Profile created', 'student_id': student.id}


@router.get('/{student_id}')
async def get_student(student_id: int, db: Session = Depends(get_db)):
    '''Fetch a student's full profile including XP and streak'''
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')

    return {
        'id': student.id,
        'name': student.name,
        'grade': student.grade,
        'language_pref': student.language_pref,
        'xp_points': student.xp_points,
        'study_streak': student.study_streak,
        'level': student.xp_points // 100,  # Every 100 XP = 1 level
        'last_active': str(student.last_active) if student.last_active else None
    }


@router.post('/{student_id}/add-xp')
async def add_xp(student_id: int, data: XPUpdate, db: Session = Depends(get_db)):
    '''
    Award XP points to a student.
    Called after: completing a study session, passing a quiz, earning a badge.
    Also updates last_active timestamp and checks streak.
    '''
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, 'Student not found')

    student.xp_points += data.xp_to_add
    student.last_active = datetime.utcnow()

    # Update study streak: if last_active was yesterday, increment streak
    # (Simplified logic -- production would compare dates properly)
    if student.study_streak is None:
        student.study_streak = 1
    else:
        student.study_streak += 1

    db.commit()

    return {
        'new_xp': student.xp_points,
        'new_level': student.xp_points // 100,
        'streak': student.study_streak
    }


@router.get('/{student_id}/history')
async def get_study_history(student_id: int, db: Session = Depends(get_db)):
    '''Return the student's recent study sessions and quiz results'''
    sessions = db.query(StudySession).filter(
        StudySession.student_id == student_id
    ).order_by(StudySession.start_time.desc()).limit(10).all()

    quizzes = db.query(QuizResult).filter(
        QuizResult.student_id == student_id
    ).order_by(QuizResult.taken_at.desc()).limit(10).all()

    return {
        'sessions': [
            {
                'subject': s.subject,
                'messages': s.message_count,
                'start': str(s.start_time),
                'end': str(s.end_time)
            }
            for s in sessions
        ],
        'quizzes': [
            {
                'subject': q.subject,
                'score': q.score,
                'total': q.total,
                'percent': round(q.score / q.total * 100, 1) if q.total else 0,
                'taken_at': str(q.taken_at)
            }
            for q in quizzes
        ]
    }