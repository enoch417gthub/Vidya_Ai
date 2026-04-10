# scripts/deploy_school.py
# ============================================================
# School Deployment Script - Fully Offline Setup
# Run this on a school PC after copying the project folder.
# Automates: venv creation, dependency install, DB init, health check
# 
# Usage: python scripts/deploy_school.py
# ============================================================

import os
import sys
import subprocess
import shutil

def run_cmd(cmd, desc):
    """Run a shell command and print progress"""
    print(f'\n>> {desc}...')
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f'ERROR: {desc} failed!')
        sys.exit(1)
    print('   Done.')

def main():
    print('=' * 60)
    print('VIDYA AI - School Deployment Setup')
    print('=' * 60)
    
    # Get the project root (where this script is located)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    print(f'Project directory: {project_root}')
    
    # Step 1: Create virtual environment
    if not os.path.exists('venv'):
        run_cmd('python -m venv venv', 'Creating virtual environment')
    else:
        print('\n>> Virtual environment already exists, skipping...')
    
    # Step 2: Determine pip path based on OS
    if sys.platform == 'win32':
        pip_path = 'venv\\Scripts\\pip'
        python_path = 'venv\\Scripts\\python'
    else:
        pip_path = 'venv/bin/pip'
        python_path = 'venv/bin/python'
    
    # Step 3: Upgrade pip
    run_cmd(f'{python_path} -m pip install --upgrade pip', 'Upgrading pip')
    
    # Step 4: Install requirements
    if os.path.exists('requirements.txt'):
        run_cmd(f'{pip_path} install -r requirements.txt', 'Installing Python packages')
    else:
        print('\n>> WARNING: requirements.txt not found!')
    
    # Step 5: Create .env from example if it doesn't exist
    if not os.path.exists('.env') and os.path.exists('.env.example'):
        shutil.copy('.env.example', '.env')
        print('\n>> Created .env from template - please review settings!')
    
    # Step 6: Create required directories
    directories = ['models/llm', 'models/embeddings', 'knowledge_base', 
                   'database', 'exports', 'logs']
    for d in directories:
        os.makedirs(d, exist_ok=True)
    print('\n>> Created all required directories')
    
    # Step 7: Initialize the database
    if os.path.exists('scripts/init_db.py'):
        run_cmd(f'{python_path} scripts/init_db.py', 'Initializing database')
    
    # Step 8: Run health check
    if os.path.exists('scripts/health_check.py'):
        run_cmd(f'{python_path} scripts/health_check.py', 'Running health check')
    
    # Done!
    print('\n' + '=' * 60)
    print(' Setup Complete!')
    print('=' * 60)
    print('\n Next steps:')
    print(' 1. Place your GGUF model in: models/llm/')
    print(' 2. Run: python app/run.py')
    print(' 3. Or double-click: run.bat (Windows) / ./run.sh (Linux/macOS)')
    print('=' * 60)

if __name__ == '__main__':
    main()