# app/api/routes/chat.py
# ============================================================
# /api/chat endpoints — handles student questions
# POST /api/chat/ask -> returns full answer (blocking)
# POST /api/chat/stream -> returns streaming response (SSE)
# ============================================================
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger
import json
from app.core.rag_pipeline import answer_question, answer_question_streaming

router = APIRouter()


class ChatRequest(BaseModel):
    '''Request body for the chat endpoints'''
    question: str      # The student's question
    grade: str         # e.g. 'grade_10'
    subject: str       # e.g. 'physics'
    language: str = 'en'  # Response language code


@router.post('/ask')
async def ask_question(req: ChatRequest):
    '''
    Answer a student question using RAG.
    Returns the full answer + source citations in one response.
    '''
    try:
        logger.info(f'Chat request: {req.question[:60]} [{req.grade}/{req.subject}]')

        answer, sources = answer_question(
            question=req.question,
            grade=req.grade,
            subject=req.subject,
        )

        # Format sources for the UI citation panel
        formatted_sources = [
            {
                'source': s.get('source', 'Unknown'),
                'page': s.get('page_number', '?'),
                'excerpt': s['content'][:200] + '...' if len(s['content']) > 200 else s['content'],
                'score': round(s.get('rrf_score', 0), 4)
            }
            for s in sources
        ]

        return {
            'answer': answer,
            'sources': formatted_sources,
            'question': req.question
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f'Chat error: {e}')
        raise HTTPException(status_code=500, detail='Internal AI error')


@router.post('/stream')
async def stream_answer(req: ChatRequest):
    '''
    Streaming chat endpoint — returns Server-Sent Events.
    UI receives tokens one at a time for live typing effect.
    '''
    def generate():
        for token in answer_question_streaming(req.question, req.grade, req.subject):
            # SSE format: 'data: ...\n\n'
            yield f'data: {json.dumps({"token": token})}\n\n'
        yield 'data: [DONE]\n\n'  # Signal stream completion

    return StreamingResponse(generate(), media_type='text/event-stream')