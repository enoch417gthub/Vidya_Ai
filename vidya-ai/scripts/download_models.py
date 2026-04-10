# scripts/download_models.py
# ============================================================
# Downloads all required AI models for VIDYA AI.
# Run this script ONCE on a machine with internet access.
# Then copy the downloaded models/ folder to school PCs via USB.
#
# Usage: python scripts/download_models.py
# Optional flags:
# --skip-llm Skip the large LLM model (download manually)
# --skip-translation Skip IndicTrans2 translation models
# --model mistral Download Mistral 7B instead of LLaMA 3 8B
# ============================================================
import os
import sys
import argparse
import urllib.request
from pathlib import Path

# Ensure we can import from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ---- Model configurations ----
MODELS = {
    'llama3-8b': {
        'filename': 'Meta-Llama-3-8B-Instruct-Q4_K_M.gguf',
        'url': 'https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf',
        'size_gb': 4.9,
        'dest': 'models/llm/'
    },
    'mistral-7b': {
        'filename': 'mistral-7b-instruct-v0.2.Q4_K_M.gguf',
        'url': 'https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf',
        'size_gb': 4.1,
        'dest': 'models/llm/'
    },
    'phi2': {
        'filename': 'phi-2.Q4_K_M.gguf',
        'url': 'https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi2.Q4_K_M.gguf',
        'size_gb': 1.6,
        'dest': 'models/llm/'
    }
}


def download_with_progress(url: str, dest_path: str, label: str):
    '''
    Download a file from URL to dest_path with a simple progress display.
    Shows percentage and downloaded MB in the terminal.
    '''
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    if os.path.exists(dest_path):
        print(f' [SKIP] {label} already exists at {dest_path}')
        return

    print(f' Downloading {label}...')
    print(f' URL: {url}')

    def progress_hook(count, block_size, total_size):
        if total_size > 0:
            pct = count * block_size / total_size * 100
            downloaded_mb = count * block_size / 1024 / 1024
            total_mb = total_size / 1024 / 1024
            print(f'\r [{pct:.1f}%] {downloaded_mb:.1f} MB / {total_mb:.1f} MB ', end='')

    try:
        urllib.request.urlretrieve(url, dest_path, reporthook=progress_hook)
        print(f'\n Done: {dest_path}')
    except Exception as e:
        print(f'\n ERROR downloading {label}: {e}')
        if os.path.exists(dest_path):
            os.remove(dest_path)  # Remove partial download
        raise


def download_embedding_model():
    '''
    Download sentence-transformers embedding model.
    Uses HuggingFace hub (cached locally to models/embeddings/).
    '''
    print('\n[2] Downloading embedding model: all-MiniLM-L6-v2...')
    print(' (This will be cached in models/embeddings/)')

    os.environ['TRANSFORMERS_CACHE'] = './models/embeddings'
    os.environ['HF_HOME'] = './models/embeddings'

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(
            'sentence-transformers/all-MiniLM-L6-v2',
            cache_folder='./models/embeddings'
        )
        # Test it works
        _ = model.encode('test sentence')
        print(' Embedding model downloaded and verified!')
    except ImportError:
        print(' ERROR: sentence-transformers not installed.')
        print(' Run: pip install sentence-transformers')


def download_indicTrans2():
    '''
    Download IndicTrans2 translation models using huggingface_hub.
    Two models: indic-to-en and en-to-indic (about 1.2GB each).
    '''
    print('\n[3] Downloading IndicTrans2 translation models...')

    try:
        from huggingface_hub import snapshot_download

        print(' Downloading indic-to-en model (~1.2GB)...')
        snapshot_download(
            repo_id='ai4bharat/indictrans2-indic-en-1B',
            local_dir='./models/translation/indic-en',
            ignore_patterns=['*.msgpack', '*.h5']  # Skip unnecessary formats
        )

        print(' Downloading en-to-indic model (~1.2GB)...')
        snapshot_download(
            repo_id='ai4bharat/indictrans2-en-indic-1B',
            local_dir='./models/translation/en-indic',
            ignore_patterns=['*.msgpack', '*.h5']
        )

        print(' IndicTrans2 models downloaded!')

    except ImportError:
        print(' ERROR: huggingface_hub not installed.')
        print(' Run: pip install huggingface_hub')
    except Exception as e:
        print(f' WARNING: IndicTrans2 download failed: {e}')
        print(' Translation will be unavailable. Core app still works.')


def main():
    parser = argparse.ArgumentParser(description='VIDYA AI Model Downloader')
    parser.add_argument('--model', default='llama3-8b',
                        choices=['llama3-8b', 'mistral-7b', 'phi2'],
                        help='Which LLM to download')
    parser.add_argument('--skip-llm', action='store_true')
    parser.add_argument('--skip-translation', action='store_true')
    args = parser.parse_args()

    print('=' * 55)
    print(' VIDYA AI -- Model Downloader')
    print(' Internet required. Run once. Copy to USB after.')
    print('=' * 55)

    # Step 1: LLM model
    if not args.skip_llm:
        cfg = MODELS[args.model]
        print(f'\n[1] Downloading LLM: {args.model} (~{cfg["size_gb"]}GB)...')
        dest = os.path.join(cfg['dest'], cfg['filename'])
        download_with_progress(cfg['url'], dest, args.model)
    else:
        print('\n[1] Skipping LLM download (--skip-llm)')

    # Step 2: Embedding model
    download_embedding_model()

    # Step 3: Translation models
    if not args.skip_translation:
        download_indicTrans2()
    else:
        print('\n[3] Skipping translation models (--skip-translation)')

    print('\n' + '=' * 55)
    print(' All downloads complete!')
    print(' Copy the models/ folder to school PCs via USB.')
    print('=' * 55)


if __name__ == '__main__':
    main()