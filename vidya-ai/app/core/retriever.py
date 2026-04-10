# app/core/retriever.py
# ============================================================
# Hybrid retriever: FAISS (semantic) + BM25 (keyword)
# Reciprocal Rank Fusion merges both result lists
# This beats either method alone for Q&A retrieval tasks
# ============================================================
import os
import json
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from typing import List, Dict, Tuple
from loguru import logger
from app.core.embedder import embed_text

# Cache: {index_path: faiss.Index} — avoid reloading same index repeatedly
_faiss_cache: Dict[str, faiss.Index] = {}
_chunk_cache: Dict[str, List[Dict]] = {}  # {index_path: [chunk_dicts]}


def load_faiss_index(index_path: str) -> Tuple[faiss.Index, List[Dict]]:
    '''
    Load a FAISS index and its corresponding chunk metadata from disk.
    Chunks JSON file stores: content, page_number, doc_id, source filename
    '''
    if index_path in _faiss_cache:
        return _faiss_cache[index_path], _chunk_cache[index_path]

    if not os.path.exists(index_path):
        raise FileNotFoundError(f'FAISS index not found: {index_path}')

    # Load the binary FAISS index
    index = faiss.read_index(index_path)

    # Load chunk metadata (stored as JSON alongside .faiss file)
    chunks_path = index_path.replace('.faiss', '_chunks.json')
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    # Cache for this session
    _faiss_cache[index_path] = index
    _chunk_cache[index_path] = chunks

    logger.info(f'Loaded FAISS index: {index_path} ({index.ntotal} vectors)')
    return index, chunks


def faiss_search(index_path: str, query: str, top_k: int = 6) -> List[Dict]:
    '''
    Semantic search using FAISS.
    Finds chunks whose meaning is closest to the query.
    Returns top_k chunks with their similarity scores
    '''
    index, chunks = load_faiss_index(index_path)
    query_vector = embed_text(query).reshape(1, -1)  # FAISS needs 2D array

    # Search: returns distances and indices of top_k nearest vectors
    # Distance here is L2 (lower=more similar) since we didn't normalize
    distances, indices = index.search(query_vector, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:  # -1 means no result found (index smaller than top_k)
            continue
        chunk = chunks[idx].copy()
        chunk['faiss_score'] = float(1.0 / (1.0 + dist))  # Convert distance to similarity
        chunk['rank_faiss'] = len(results) + 1
        results.append(chunk)
    return results


def bm25_search(chunks: List[Dict], query: str, top_k: int = 6) -> List[Dict]:
    '''
    Keyword search using BM25 algorithm.
    Good at finding exact term matches the semantic model might miss.
    '''
    # Tokenize all chunk contents (simple word split)
    tokenized_corpus = [c['content'].lower().split() for c in chunks]
    bm25 = BM25Okapi(tokenized_corpus)

    # Score all chunks against the query
    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)

    # Get top_k chunk indices by score
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for rank, idx in enumerate(top_indices):
        if scores[idx] > 0:  # Only include chunks with non-zero score
            chunk = chunks[idx].copy()
            chunk['bm25_score'] = float(scores[idx])
            chunk['rank_bm25'] = rank + 1
            results.append(chunk)
    return results


def reciprocal_rank_fusion(faiss_results, bm25_results, k=60) -> List[Dict]:
    '''
    Merge FAISS and BM25 results using Reciprocal Rank Fusion (RRF).
    RRF score = 1/(k + rank_in_list1) + 1/(k + rank_in_list2)
    k=60 is a standard constant that prevents top ranks from dominating.
    '''
    scores: Dict[str, float] = {}  # chunk_id -> RRF score
    chunks_map: Dict[str, Dict] = {}  # chunk_id -> chunk dict

    # Add FAISS scores
    for rank, chunk in enumerate(faiss_results):
        cid = str(chunk.get('id', rank))
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        chunks_map[cid] = chunk

    # Add BM25 scores
    for rank, chunk in enumerate(bm25_results):
        cid = str(chunk.get('id', f'bm25_{rank}'))
        scores[cid] = scores.get(cid, 0) + 1.0 / (k + rank + 1)
        chunks_map[cid] = chunk

    # Sort by combined RRF score (descending)
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    merged = []
    for cid in sorted_ids:
        chunk = chunks_map[cid].copy()
        chunk['rrf_score'] = scores[cid]
        merged.append(chunk)
    return merged


def hybrid_search(index_path: str, query: str, top_k: int = 6) -> List[Dict]:
    '''
    Main retrieval function — combines FAISS + BM25 + RRF.
    This is called by the RAG pipeline for every student question.
    '''
    _, chunks = load_faiss_index(index_path)
    faiss_res = faiss_search(index_path, query, top_k=top_k)
    bm25_res = bm25_search(chunks, query, top_k=top_k)
    merged = reciprocal_rank_fusion(faiss_res, bm25_res)
    return merged[:top_k]  # Return final top_k results