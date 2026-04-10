# scripts/health_check.py
# Run before starting: python scripts/health_check.py
# Verifies all required components are present and working
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

PASS = '[OK]'
FAIL = '[FAIL]'
errors = []


def check(label, condition, fix_hint=''):
    if condition:
        print(f' {PASS} {label}')
    else:
        print(f' {FAIL} {label}')
        if fix_hint:
            print(f' FIX: {fix_hint}')
        errors.append(label)


print('\n=== VIDYA AI Health Check ===')

# 1. Check Python version
import platform
ver = sys.version_info
check('Python version >= 3.10', ver.major == 3 and ver.minor >= 10,
      'Install Python 3.10 or 3.11')

# 2. Check required libraries
libs = ['fastapi', 'llama_cpp', 'faiss', 'sentence_transformers',
        'PyQt6', 'sqlalchemy', 'fitz', 'pptx', 'docx', 'pytesseract']

for lib in libs:
    try:
        __import__(lib)
        check(f'Library: {lib}', True)
    except ImportError:
        check(f'Library: {lib}', False, f'pip install {lib}')

# 3. Check LLM model file
models_dir = os.getenv('MODELS_DIR', './models')
model_file = os.getenv('LLM_MODEL_FILENAME', 'Meta-Llama-3-8B-Instruct-Q4_K_M.gguf')
model_path = os.path.join(models_dir, 'llm', model_file)
check('LLM model file exists', os.path.exists(model_path),
      f'Download GGUF model and place at: {model_path}')

# 4. Check database directory
db_path = os.getenv('DATABASE_PATH', './database/vidya.db')
check('Database directory', os.path.isdir(os.path.dirname(db_path)),
      'Run: python scripts/init_db.py')

# 5. Check knowledge base directory
kb_dir = os.getenv('KNOWLEDGE_BASE_DIR', './knowledge_base')
check('Knowledge base dir', os.path.isdir(kb_dir),
      f'mkdir {kb_dir}')

# Summary
print(f'\nResult: {len(errors)} issue(s) found.')
if errors:
    print('Fix the above issues before running VIDYA AI.')
    sys.exit(1)
else:
    print('All checks passed! Run: python app/run.py')