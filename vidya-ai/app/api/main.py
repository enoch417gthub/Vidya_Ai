# app/api/main.py
# ============================================================
# FastAPI application — the backend REST server
# Runs on localhost:8000 (not accessible from internet)
# The PyQt6 UI communicates with this via HTTP
# ============================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
from app.db.database import engine, Base
from app.api.routes import chat, upload, search, student


@asynccontextmanager
async def lifespan(app: FastAPI):
    '''
    Startup and shutdown events.
    On startup: create DB tables, pre-warm the LLM.
    '''
    logger.info('Starting VIDYA AI backend...')
    Base.metadata.create_all(bind=engine)  # Create tables if not exist
    logger.info('Database ready')
    yield  # App runs here
    logger.info('Shutting down VIDYA AI...')


# Create the FastAPI app instance
app = FastAPI(
    title='VIDYA AI API',
    description='Offline AI Tutor for Rural Education',
    version='1.0.0',
    lifespan=lifespan
)

# CORS: Allow the PyQt6 UI to call this API from localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost', 'http://127.0.0.1'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# Register route modules
app.include_router(chat.router, prefix='/api/chat', tags=['Chat'])
app.include_router(upload.router, prefix='/api/upload', tags=['Upload'])
app.include_router(search.router, prefix='/api/search', tags=['Search'])
app.include_router(student.router, prefix='/api/student', tags=['Student'])


@app.get('/api/health')
async def health_check():
    '''Simple health check endpoint — returns ok if server is running'''
    return {'status': 'ok', 'message': 'VIDYA AI is running'}