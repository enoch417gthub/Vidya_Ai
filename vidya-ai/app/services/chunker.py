# app/services/chunker.py
# ============================================================
# Splits extracted text into chunks suitable for embedding
# Why chunk? LLMs have context limits; embedding works best on
# focused paragraphs, not entire documents at once.
# ============================================================
import os
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Chunk size in characters (approx 512 tokens at ~4 chars/token)
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 512)) * 4
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 50)) * 4

# RecursiveCharacterTextSplitter: tries to split at paragraphs first,
# then sentences, then words — preserving natural boundaries
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=['\n\n', '\n', '. ', ', ', ' ', '']  # Priority order
)


def chunk_pages(pages: List[Dict], doc_id: int, source: str) -> List[Dict]:
    '''
    Split a list of extracted pages into text chunks.
    Each chunk includes metadata for source citation in answers.
    Args:
        pages: output from parser.extract_text()
        doc_id: database ID of the parent document
        source: filename for display in citations
    Returns: list of chunk dicts ready for embedding
    '''
    all_chunks = []
    chunk_idx = 0

    for page_data in pages:
        page_num = page_data['page']
        text = page_data['text']

        # Split this page's text into chunks
        page_chunks = splitter.split_text(text)

        for chunk_text in page_chunks:
            if len(chunk_text.strip()) < 30:  # Skip tiny meaningless chunks
                continue

            all_chunks.append({
                'id': chunk_idx,               # Position in this document's chunk list
                'doc_id': doc_id,              # Parent document ID
                'chunk_index': chunk_idx,      # Global index for FAISS mapping
                'content': chunk_text.strip(),
                'page_number': page_num,
                'source': source,              # e.g. 'NCERT_Physics_Ch1.pdf'
            })
            chunk_idx += 1

    return all_chunks