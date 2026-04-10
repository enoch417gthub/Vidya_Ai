# app/services/quiz_gen.py
# ============================================================
# Generates quizzes and flashcards from the knowledge base.
# Prompts the LLM to produce JSON-structured questions.
# JSON output is then parsed and displayed in the UI.
# ============================================================
import os
import json
import re
from typing import List, Dict
from loguru import logger
from app.core.retriever import hybrid_search
from app.core.llm_engine import generate_response


def build_quiz_prompt(topic: str, context: str, num_questions: int, q_type: str) -> str:
    '''Build LLM prompt that requests JSON-structured quiz questions'''
    type_instruction = {
        'mcq': (
            f'Generate {num_questions} multiple-choice questions (MCQ). '
            'Each must have 4 options (A, B, C, D) and exactly one correct answer. '
            'Return ONLY valid JSON array, no other text. Format: '
            '[{"question":"...","options":{"A":"...","B":"...","C":"...","D":"..."},"answer":"A","explanation":"..."}]'
        ),
        'truefalse': (
            f'Generate {num_questions} True/False statements about this topic. '
            'Return ONLY valid JSON array. Format: '
            '[{"statement":"...","answer":true,"explanation":"..."}]'
        ),
        'flashcard': (
            f'Generate {num_questions} flashcards for memorization. '
            'Each flashcard has a term/question on the front and definition/answer on the back. '
            'Return ONLY valid JSON array. Format: '
            '[{"front":"...","back":"..."}]'
        ),
    }

    instruction = type_instruction.get(q_type, type_instruction['mcq'])

    return f'''<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a quiz generator. Generate questions ONLY from the provided content.
You MUST return only valid JSON. No prose, no markdown, no explanation outside the JSON.<|eot_id|>
<|start_header_id|>user<|end_header_id|>
TOPIC: {topic}
CONTENT: {context}
TASK: {instruction}<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>['''


def parse_json_response(raw: str) -> list:
    '''
    Safely parse the LLM JSON output.
    LLMs sometimes add extra text before/after JSON -- this strips it.
    '''
    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Find JSON array in the response using regex
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning(f'Failed to parse quiz JSON from LLM output: {raw[:200]}')
    return []  # Return empty list on parse failure (graceful degradation)


def generate_quiz(
    grade: str,
    subject: str,
    topic: str,
    num_questions: int = 10,
    q_type: str = 'mcq'  # 'mcq', 'truefalse', or 'flashcard'
) -> List[Dict]:
    '''
    Generate quiz questions for a given topic.
    Returns a list of question dicts (structure depends on q_type).
    '''
    kb_dir = os.getenv('KNOWLEDGE_BASE_DIR', './knowledge_base')
    index_path = os.path.join(kb_dir, grade, subject, f'{subject}.faiss')

    # Retrieve relevant context from knowledge base
    chunks = hybrid_search(index_path, topic, top_k=6)
    if not chunks:
        return []

    context = ' '.join([c['content'] for c in chunks])[:2000]  # Limit context size

    # Generate questions via LLM
    prompt = build_quiz_prompt(topic, context, num_questions, q_type)
    raw_response = generate_response(prompt, max_tokens=1000)

    # The prompt ends with '[' so prepend it for valid JSON
    raw_response = '[' + raw_response
    questions = parse_json_response(raw_response)

    logger.info(f'Generated {len(questions)} {q_type} questions for topic: {topic}')
    return questions