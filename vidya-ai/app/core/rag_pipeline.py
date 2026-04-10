# app/core/rag_pipeline.py
# ============================================================
# RAG (Retrieval-Augmented Generation) pipeline
# Flow: question -> retrieve chunks -> build prompt -> LLM -> answer
# This ensures answers are grounded in the school's actual content
# ============================================================
import os
from typing import List, Dict, Tuple
from loguru import logger
from app.core.retriever import hybrid_search
from app.core.llm_engine import generate_response, generate_streaming


def get_index_path(grade: str, subject: str) -> str:
    '''
    Build the path to the FAISS index for a given grade + subject.
    e.g. grade='grade_10', subject='physics' ->
    ./knowledge_base/grade_10/physics/physics.faiss
    '''
    kb_dir = os.getenv('KNOWLEDGE_BASE_DIR', './knowledge_base')
    return os.path.join(kb_dir, grade, subject, f'{subject}.faiss')


def build_rag_prompt(question: str, context_chunks: List[Dict], subject: str) -> str:
    '''
    Build the final prompt sent to the LLM.
    Uses LLaMA 3 instruction format: [INST] ... [/INST]
    The context chunks are inserted so the LLM answers from them.
    '''
    # Format retrieved chunks into a readable context block
    context_parts = []
    for i, chunk in enumerate(context_chunks):
        src = chunk.get('source', 'Unknown source')
        page = chunk.get('page_number', '?')
        content = chunk['content'].strip()
        context_parts.append(f'[Source {i+1}: {src}, Page {page}]\n{content}')

    context_text = '\n\n'.join(context_parts)

    # System instruction for the LLM
    system_msg = f'''You are VIDYA AI, a helpful and accurate tutor for {subject} students.
Use ONLY the information provided in the context below to answer the question.
If the answer is not in the context, say: 'This topic is not covered in the uploaded materials.'
Be clear, educational, and use examples where helpful.
Always mention which source your answer came from.'''

    # LLaMA 3 instruction format
    prompt = f'''<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_msg}<|eot_id|>
<|start_header_id|>user<|end_header_id|>
CONTEXT FROM UPLOADED MATERIALS:
{context_text}

STUDENT QUESTION: {question}<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>'''

    return prompt


def answer_question(
    question: str,
    grade: str,
    subject: str,
    top_k: int = 6
) -> Tuple[str, List[Dict]]:
    '''
    Main RAG function — given a question, returns an answer + source citations.
    Steps: retrieve -> build prompt -> generate -> return
    '''
    index_path = get_index_path(grade, subject)

    # Step 1: Retrieve top-k relevant chunks from the knowledge base
    logger.info(f'Retrieving context for: {question[:60]}...')
    chunks = hybrid_search(index_path, question, top_k=top_k)

    if not chunks:
        return ('No relevant content found in the uploaded materials for this question.', [])

    # Step 2: Build the RAG prompt with retrieved context
    prompt = build_rag_prompt(question, chunks, subject)

    # Step 3: Generate the answer using the local LLM
    logger.info('Generating LLM response...')
    answer = generate_response(prompt, max_tokens=int(os.getenv('LLM_MAX_TOKENS', 512)))

    # Step 4: Return the answer and the source chunks used
    return answer, chunks


def answer_question_streaming(question: str, grade: str, subject: str):
    '''Streaming version — yields answer tokens for live UI display'''
    index_path = get_index_path(grade, subject)
    chunks = hybrid_search(index_path, question, top_k=6)

    if not chunks:
        yield 'No relevant content found in the uploaded materials.'
        return

    prompt = build_rag_prompt(question, chunks, subject)
    yield from generate_streaming(prompt)  # Stream tokens to caller