#!/bin/bash
# ================================================
# VIDYA AI — Linux/macOS Launcher
# Make executable: chmod +x run.sh
# Run: ./run.sh
# ================================================

echo 'Starting VIDYA AI...'

# Activate virtual environment
source venv/bin/activate

# Initialize database on first run (safe to run multiple times)
python scripts/init_db.py

# Launch the application
python app/run.py