# app/db/database.py
# ============================================================
# Database engine and session management
# SQLite is used -- no external DB server needed (perfect for offline)
# ============================================================
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()  # Load settings from .env file

# Get the database path from environment variable
# Default: ./database/vidya.db (relative to project root)
DATABASE_PATH = os.getenv('DATABASE_PATH', './database/vidya.db')

# Ensure the database directory exists before creating the file
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# SQLAlchemy connection URL for SQLite
# 'check_same_thread=False' required for FastAPI's async usage
SQLALCHEMY_DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# Create the database engine
# connect_args: allows SQLite to work across different threads
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={'check_same_thread': False},
    echo=False  # Set to True to log all SQL queries (debug mode)
)

# Session factory — creates individual DB sessions
# autocommit=False: we commit manually (gives us transaction control)
# autoflush=False: don't auto-flush (prevents premature writes)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()

def get_db():
    '''
    FastAPI dependency — yields a database session.
    Ensures session is always closed after request completes.
    Usage: db: Session = Depends(get_db)
    '''
    db = SessionLocal()
    try:
        yield db  # Provide session to the route handler
    finally:
        db.close()  # Always close, even if an error occurred