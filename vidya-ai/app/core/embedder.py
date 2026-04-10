# app/core/embedder.py
# ============================================================
# Embedding model wrapper
# Converts text strings into float vectors for semantic search
# Model: all-MiniLM-L6-v2 (22MB, runs on CPU, 384 dimensions)
# ============================================================
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from loguru import logger

# Singleton pattern — load model once, reuse for all requests
_embedder_instance = None


def get_embedder() -> SentenceTransformer:
    '''Returns the singleton embedding model instance'''
    global _embedder_instance
    if _embedder_instance is None:
        model_name = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
        logger.info(f'Loading embedding model: {model_name}')
        # cache_folder: saves model locally so no internet needed after first load
        _embedder_instance = SentenceTransformer(
            model_name,
            cache_folder='./models/embeddings'
        )
        logger.info('Embedding model loaded successfully')
    return _embedder_instance


def embed_text(text: str) -> np.ndarray:
    '''
    Embed a single text string into a vector.
    Returns: numpy array of shape (384,) — one vector
    '''
    model = get_embedder()
    # normalize_embeddings=True: makes cosine similarity = dot product
    # This improves retrieval accuracy
    vector = model.encode(text, normalize_embeddings=True)
    return vector.astype(np.float32)  # FAISS requires float32


def embed_batch(texts: list[str]) -> np.ndarray:
    '''
    Embed a list of texts in one efficient batch.
    Returns: numpy array of shape (N, 384) — N vectors
    Used during document indexing (much faster than one-by-one)
    '''
    model = get_embedder()
    # batch_size=64: process 64 chunks at a time to control memory
    # show_progress_bar=True: visible progress during indexing
    vectors = model.encode(
        texts,
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=True
    )
    return vectors.astype(np.float32)