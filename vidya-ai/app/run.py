# app/run.py
# ============================================================
# Combined launcher: starts FastAPI backend + PyQt6 UI together
# Run with: python app/run.py
# ============================================================

import sys
import os

# Add the project root to Python path BEFORE any imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import threading
import time
import uvicorn
from loguru import logger

# Configure logging
os.makedirs('logs', exist_ok=True)
logger.add('logs/vidya_ai.log', rotation='10 MB', retention='7 days')


def start_backend():
    """Start FastAPI + Uvicorn in a background thread"""
    logger.info('Starting FastAPI backend on http://127.0.0.1:8000')
    
    # Use absolute import path
    uvicorn.run(
        'app.api.main:app',
        host='127.0.0.1',
        port=8000,
        log_level='warning',
        reload=False
    )


def wait_for_backend(max_wait: int = 30) -> bool:
    """Poll until the backend is ready to accept connections"""
    import httpx
    for i in range(max_wait):
        try:
            r = httpx.get('http://127.0.0.1:8000/api/health', timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
        logger.info(f'Waiting for backend... ({i+1}/{max_wait})')
    return False


def main():
    """Main entry point - starts backend then UI"""
    # Step 1: Start backend in a daemon thread
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Step 2: Wait for backend to be ready
    logger.info('Waiting for backend to start...')
    if not wait_for_backend():
        logger.error('Backend failed to start within 30 seconds!')
        logger.error('Check if port 8000 is available or if there are import errors')
        sys.exit(1)
    
    logger.info('Backend ready!')
    
    # Step 3: Start PyQt6 UI on the main thread
    try:
        from PyQt6.QtWidgets import QApplication
        from app.ui.main_window import MainWindow
        
        app = QApplication(sys.argv)
        app.setApplicationName('VIDYA AI')
        
        window = MainWindow()
        window.show()
        
        logger.info('VIDYA AI UI started successfully')
        sys.exit(app.exec())
    except ImportError as e:
        logger.error(f'Failed to import UI modules: {e}')
        logger.error('Make sure PyQt6 is installed: pip install PyQt6')
        sys.exit(1)


if __name__ == '__main__':
    main()