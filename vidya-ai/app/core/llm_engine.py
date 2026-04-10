# app/core/llm_engine.py
# ============================================================
# Local LLM wrapper using llama-cpp-python
# Runs GGUF quantized models (LLaMA 3, Mistral) entirely on CPU
# Singleton pattern: model loads once, stays in RAM for fast responses
# ============================================================
import os
from llama_cpp import Llama
from loguru import logger
from typing import Generator

_llm_instance = None  # Singleton — loaded once per app session


def get_llm() -> Llama:
    '''
    Load and return the local LLM.
    First call: loads model from disk (takes 10-30 seconds).
    Subsequent calls: returns cached instance (instant).
    '''
    global _llm_instance
    if _llm_instance is None:
        models_dir = os.getenv('MODELS_DIR', './models')
        model_file = os.getenv('LLM_MODEL_FILENAME', 'Meta-Llama-3-8B-Instruct-Q4_K_M.gguf')
        model_path = os.path.join(models_dir, 'llm', model_file)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f'LLM model not found at: {model_path}\n'
                f'Download from HuggingFace and place in models/llm/'
            )

        logger.info(f'Loading LLM: {model_file} (this may take 20-30 seconds...)')

        _llm_instance = Llama(
            model_path=model_path,
            n_ctx=int(os.getenv('LLM_N_CTX', 4096)),      # Context window (tokens)
            n_threads=int(os.getenv('LLM_N_THREADS', 4)), # CPU threads
            n_gpu_layers=0,                               # 0 = CPU only; set to -1 for full GPU offload
            verbose=False,                                # Suppress llama.cpp output spam
            use_mmap=True,                                # Memory-map model file (reduces RAM usage)
        )
        logger.info('LLM loaded and ready!')
    return _llm_instance


def generate_response(prompt: str, max_tokens: int = 512) -> str:
    '''
    Generate a complete response for a given prompt.
    Blocks until generation completes.
    '''
    llm = get_llm()
    output = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=float(os.getenv('LLM_TEMPERATURE', 0.3)),
        top_p=0.9,      # Nucleus sampling — limits to top 90% probability mass
        top_k=40,       # Only consider top 40 tokens at each step
        repeat_penalty=1.1,  # Discourage repeating the same phrases
        stop=['<|end|>', '[INST]', '###', '\n\nQuestion:'],  # Stop tokens
    )
    # Extract the text from the response dict
    return output['choices'][0]['text'].strip()


def generate_streaming(prompt: str, max_tokens: int = 512) -> Generator[str, None, None]:
    '''
    Generate a streaming response — yields tokens as they are produced.
    Used by the chat UI to show text appearing word-by-word.
    '''
    llm = get_llm()
    stream = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=float(os.getenv('LLM_TEMPERATURE', 0.3)),
        top_p=0.9,
        stream=True,  # Enable streaming mode
        stop=['<|end|>', '[INST]', '###'],
    )
    for chunk in stream:
        token_text = chunk['choices'][0]['text']
        if token_text:  # Yield non-empty tokens
            yield token_text