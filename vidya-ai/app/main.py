# app/main.py
# ============================================================
# VIDYA AI -- Application Entry Point
# This is the first file executed when you launch VIDYA AI.
# It simply delegates to app/run.py which starts both the
# FastAPI backend and the PyQt6 desktop UI together.
#
# HOW TO RUN:
# python app/main.py (from project root)
# python -m app.main (as module, also from project root)
# Double-click run.bat (Windows one-click)
# ./run.sh (Linux/macOS one-click)
# ============================================================
import sys
import os

# Ensure the project root is in Python's module search path.
# This lets 'from app.core.llm_engine import ...' work correctly
# regardless of which directory you launch from.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.run import main  # Import the combined launcher


if __name__ == '__main__':
    # When run directly (python app/main.py), launch the full app.
    # main() starts FastAPI backend in background thread,
    # waits for it to be ready, then opens the PyQt6 window.
    main()