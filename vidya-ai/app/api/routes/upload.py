# app/api/routes/upload.py
# ============================================================
# /api/upload — handles admin document uploads
# Saves file, adds DB record, triggers background indexing
# ============================================================
import os
import shutil
import hashlib
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi import Depends
from sqlalchemy.orm import Session
from loguru import logger
from app.db.database import get_db
from app.db.models import Document
from app.services.indexer import index_document

router = APIRouter()
ALLOWED_EXTENSIONS = {'.pdf', '.pptx', '.ppt', '.docx', '.doc', '.txt'}


def compute_md5(filepath: str) -> str:
    '''Compute MD5 checksum to detect duplicate uploads'''
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def background_index(filepath: str, grade: str, subject: str, doc_id: int, db_path: str):
    '''
    Runs in background thread after upload completes.
    Indexes the document and updates DB record.
    '''
    from app.db.database import SessionLocal
    from datetime import datetime

    db = SessionLocal()
    try:
        chunk_count = index_document(filepath, grade, subject, doc_id)

        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.chunk_count = chunk_count
            doc.indexed = True
            doc.indexed_at = datetime.utcnow()
            db.commit()

        logger.info(f'Indexed doc_id={doc_id}: {chunk_count} chunks')

    except Exception as e:
        logger.error(f'Indexing failed for doc_id={doc_id}: {e}')
    finally:
        db.close()


@router.post('/document')
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    grade: str = Form(...),      # e.g. 'grade_10'
    subject: str = Form(...),    # e.g. 'physics'
    doc_type: str = Form('notes'),
    db: Session = Depends(get_db)
):
    '''Upload a document and trigger background indexing'''

    # Validate file extension
    ext = os.path.splitext(file.filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f'File type {ext} not supported')

    # Build save path
    kb_dir = os.getenv('KNOWLEDGE_BASE_DIR', './knowledge_base')
    raw_dir = os.path.join(kb_dir, grade, subject, 'raw')
    os.makedirs(raw_dir, exist_ok=True)
    save_path = os.path.join(raw_dir, file.filename)

    # Save file to disk
    with open(save_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(save_path)
    checksum = compute_md5(save_path)

    # Check for duplicate (same file already uploaded)
    existing = db.query(Document).filter(Document.checksum == checksum).first()
    if existing:
        os.remove(save_path)  # Delete the duplicate
        return {'message': 'Document already exists', 'doc_id': existing.id, 'duplicate': True}

    # Create database record
    doc = Document(
        filename=file.filename,
        filepath=save_path,
        subject=subject,
        grade=grade,
        doc_type=doc_type,
        file_size=file_size,
        checksum=checksum,
        indexed=False
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Kick off background indexing (doesn't block the HTTP response)
    background_tasks.add_task(
        background_index, save_path, grade, subject, doc.id, ''
    )

    return {
        'message': 'Upload successful. Indexing in progress.',
        'doc_id': doc.id,
        'filename': file.filename
    }