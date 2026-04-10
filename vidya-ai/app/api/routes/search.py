# app/api/routes/search.py
# ============================================================
# /api/search -- semantic + keyword search across the knowledge base
# Returns matching document chunks with highlights and source info.
# Does NOT call the LLM -- pure retrieval, very fast.
# ============================================================
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from loguru import logger
import os
import glob
from app.core.retriever import hybrid_search, load_faiss_index

router = APIRouter()


class SearchRequest(BaseModel):
    '''Request body for the search endpoint'''
    query: str                # The search term / question
    grade: str                # e.g. 'grade_10'
    subject: Optional[str] = None  # None = search ALL subjects in this grade
    top_k: int = 10           # How many results to return


class SearchResult(BaseModel):
    '''A single search result item'''
    source: str       # Filename of the source document
    page_number: int  # Page number in the source document
    excerpt: str      # The relevant text snippet
    subject: str      # Which subject this result belongs to
    score: float      # Relevance score (higher = more relevant)


def get_all_subject_indexes(grade: str) -> List[dict]:
    '''
    Find all .faiss index files for a given grade.
    Used when subject=None to search across ALL subjects.
    Returns: list of {subject, index_path}
    '''
    kb_dir = os.getenv('KNOWLEDGE_BASE_DIR', './knowledge_base')
    grade_dir = os.path.join(kb_dir, grade)

    if not os.path.isdir(grade_dir):
        return []

    # Find every *.faiss file recursively under this grade folder
    faiss_files = glob.glob(os.path.join(grade_dir, '*', '*.faiss'))

    results = []
    for fp in faiss_files:
        # Extract subject name from path: .../grade_10/physics/physics.faiss -> 'physics'
        subject_name = os.path.basename(os.path.dirname(fp))
        results.append({'subject': subject_name, 'index_path': fp})
    return results


@router.post('/', response_model=List[SearchResult])
async def search_knowledge_base(req: SearchRequest):
    '''
    Search the knowledge base for relevant content.
    If subject is specified, searches only that subject.
    If subject is None, searches ALL subjects in the grade.
    '''
    try:
        all_results = []

        if req.subject:
            # Search a specific subject only
            kb_dir = os.getenv('KNOWLEDGE_BASE_DIR', './knowledge_base')
            index_path = os.path.join(kb_dir, req.grade, req.subject, f'{req.subject}.faiss')

            if not os.path.exists(index_path):
                raise HTTPException(404, f'No index found for {req.grade}/{req.subject}')

            chunks = hybrid_search(index_path, req.query, top_k=req.top_k)

            for c in chunks:
                all_results.append(SearchResult(
                    source=c.get('source', 'Unknown'),
                    page_number=c.get('page_number', 0),
                    excerpt=c['content'][:300],  # Trim to 300 chars for display
                    subject=req.subject,
                    score=round(c.get('rrf_score', 0.0), 4)
                ))
        else:
            # Search ALL subjects in this grade
            indexes = get_all_subject_indexes(req.grade)

            if not indexes:
                raise HTTPException(404, f'No indexes found for grade: {req.grade}')

            for idx_info in indexes:
                try:
                    chunks = hybrid_search(idx_info['index_path'], req.query, top_k=5)

                    for c in chunks:
                        all_results.append(SearchResult(
                            source=c.get('source', 'Unknown'),
                            page_number=c.get('page_number', 0),
                            excerpt=c['content'][:300],
                            subject=idx_info['subject'],
                            score=round(c.get('rrf_score', 0.0), 4)
                        ))
                except Exception as e:
                    logger.warning(f'Search failed for {idx_info["subject"]}: {e}')

        # Sort all merged results by score descending, return top_k
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:req.top_k]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Search error: {e}')
        raise HTTPException(500, 'Search failed')


@router.get('/subjects')
async def list_subjects(grade: str = Query(..., description='e.g. grade_10')):
    '''
    List all available subjects for a given grade.
    Used by the UI dropdowns to populate subject selectors dynamically.
    '''
    indexes = get_all_subject_indexes(grade)
    subjects = [i['subject'] for i in indexes]
    return {'grade': grade, 'subjects': subjects, 'count': len(subjects)}