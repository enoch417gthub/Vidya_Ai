# app/services/indexer.py
# ============================================================
# Builds and updates FAISS vector indexes
# Each subject gets its own .faiss file + _chunks.json sidecar
# Called after every document upload
# ============================================================
import os
import json
import hashlib
import numpy as np
import faiss
from typing import List, Dict
from loguru import logger
from tqdm import tqdm
from app.core.embedder import embed_batch
from app.services.parser import extract_text
from app.services.chunker import chunk_pages


def get_subject_dir(grade: str, subject: str) -> str:
    '''Return the path to a subject's index directory, creating it if needed'''
    kb_dir = os.getenv('KNOWLEDGE_BASE_DIR', './knowledge_base')
    path = os.path.join(kb_dir, grade, subject)
    os.makedirs(path, exist_ok=True)
    return path


def load_or_create_index(subject_dir: str, subject: str, dim: int = 384):
    '''
    Load existing FAISS index or create a fresh one.
    dim=384 matches all-MiniLM-L6-v2 output size.
    IndexFlatIP: flat index using Inner Product (cosine similarity with normalized vecs)
    '''
    index_path = os.path.join(subject_dir, f'{subject}.faiss')
    chunks_path = os.path.join(subject_dir, f'{subject}_chunks.json')

    if os.path.exists(index_path):
        index = faiss.read_index(index_path)  # Load existing
        with open(chunks_path, 'r') as f:
            existing_chunks = json.load(f)
        logger.info(f'Loaded existing index: {index.ntotal} vectors')
    else:
        index = faiss.IndexFlatIP(dim)  # Create new flat Inner Product index
        existing_chunks = []
        logger.info('Created new FAISS index')

    return index, existing_chunks, index_path, chunks_path


def index_document(
    filepath: str,
    grade: str,
    subject: str,
    doc_id: int
) -> int:
    '''
    Full pipeline: file -> extract -> chunk -> embed -> index.
    Returns the number of chunks indexed.
    '''
    source_name = os.path.basename(filepath)
    subject_dir = get_subject_dir(grade, subject)

    # Step 1: Extract text from document
    logger.info(f'Parsing: {source_name}')
    pages = extract_text(filepath)

    # Step 2: Split into chunks
    chunks = chunk_pages(pages, doc_id, source_name)
    logger.info(f'Created {len(chunks)} chunks')

    if not chunks:
        logger.warning('No chunks created — document may be empty or unreadable')
        return 0

    # Step 3: Embed all chunks in one batch (efficient)
    logger.info('Generating embeddings...')
    texts = [c['content'] for c in chunks]
    embeddings = embed_batch(texts)  # Shape: (N, 384)

    # Step 4: Load or create the subject's FAISS index
    index, existing_chunks, index_path, chunks_path = load_or_create_index(
        subject_dir, subject
    )

    # Step 5: Adjust chunk IDs to be globally unique within the index
    offset = len(existing_chunks)
    for i, chunk in enumerate(chunks):
        chunk['id'] = offset + i

    # Step 6: Add new embeddings to the FAISS index
    index.add(embeddings)

    # Step 7: Save updated index and chunks to disk
    faiss.write_index(index, index_path)

    all_chunks = existing_chunks + chunks
    with open(chunks_path, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    logger.info(f'Index updated: {index.ntotal} total vectors in {index_path}')
    return len(chunks)