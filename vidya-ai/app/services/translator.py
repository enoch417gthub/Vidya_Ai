# app/services/translator.py
# ============================================================
# Offline translation service using IndicTrans2 (AI4Bharat)
# Translates between English and 8+ Indian languages.
# Falls back to a no-op (returns original text) if model not loaded.
#
# SUPPORTED LANGUAGE CODES:
# en=English, hi=Hindi, ta=Tamil, te=Telugu,
# kn=Kannada, bn=Bengali, mr=Marathi, gu=Gujarati
# ============================================================
import os
from typing import Optional
from loguru import logger

# Language code to IndicTrans2 language tag mapping
LANG_MAP = {
    'en': 'eng_Latn',
    'hi': 'hin_Deva',
    'ta': 'tam_Taml',
    'te': 'tel_Telu',
    'kn': 'kan_Knda',
    'bn': 'ben_Beng',
    'mr': 'mar_Deva',
    'gu': 'guj_Gujr',
    'or': 'ory_Orya',
    'pa': 'pan_Guru',
}

# Singleton holders for the two translation pipelines
_indic_to_en = None      # Translates ANY Indian language -> English
_en_to_indic = None      # Translates English -> ANY Indian language
_translation_available = None  # None=not checked, True/False after first call


def _load_indicTrans2():
    '''
    Attempt to load IndicTrans2 models.
    Sets _translation_available=True if successful, False if not installed.
    '''
    global _indic_to_en, _en_to_indic, _translation_available

    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        from IndicTransToolkit import IndicProcessor

        translation_dir = os.path.join(os.getenv('MODELS_DIR', './models'), 'translation')
        model_i2e = os.path.join(translation_dir, 'indic-en')
        model_e2i = os.path.join(translation_dir, 'en-indic')

        if os.path.isdir(model_i2e) and os.path.isdir(model_e2i):
            logger.info('Loading IndicTrans2 models...')
            _indic_to_en = {
                'tokenizer': AutoTokenizer.from_pretrained(model_i2e, trust_remote_code=True),
                'model': AutoModelForSeq2SeqLM.from_pretrained(model_i2e),
                'processor': IndicProcessor(inference=True)
            }
            _en_to_indic = {
                'tokenizer': AutoTokenizer.from_pretrained(model_e2i, trust_remote_code=True),
                'model': AutoModelForSeq2SeqLM.from_pretrained(model_e2i),
                'processor': IndicProcessor(inference=True)
            }
            _translation_available = True
            logger.info('IndicTrans2 loaded successfully')
        else:
            logger.warning(f'IndicTrans2 model dirs not found in {translation_dir}')
            _translation_available = False

    except ImportError:
        logger.warning('IndicTrans2 not installed. Translation unavailable.')
        logger.warning('To enable: pip install indic-trans IndicTransToolkit')
        _translation_available = False


def _run_translation(pipeline: dict, text: str, src_lang: str, tgt_lang: str) -> str:
    '''
    Run a single translation using an IndicTrans2 pipeline dict.
    pipeline: contains tokenizer, model, and processor.
    '''
    processor = pipeline['processor']
    tokenizer = pipeline['tokenizer']
    model = pipeline['model']

    # Step 1: Pre-process text (IndicTrans2 expects specific input format)
    batch = processor.preprocess_batch([text], src_lang=src_lang, tgt_lang=tgt_lang)

    # Step 2: Tokenize
    inputs = tokenizer(
        batch, return_tensors='pt', padding=True, truncation=True, max_length=512
    )

    # Step 3: Generate translation
    import torch
    with torch.no_grad():  # Disable gradient tracking (not needed for inference)
        outputs = model.generate(**inputs, num_beams=4, max_length=512)

    # Step 4: Decode output tokens back to text
    decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)

    # Step 5: Post-process (remove artifacts, fix spacing)
    result = processor.postprocess_batch(decoded, lang=tgt_lang)

    return result[0] if result else text


def translate(text: str, src_lang: str, tgt_lang: str) -> str:
    '''
    Main translation function.
    If src_lang == tgt_lang, returns text unchanged (no translation needed).
    If translation models are unavailable, returns original text with a warning.

    Args:
        text: The text to translate
        src_lang: Source language code (e.g. 'hi' for Hindi)
        tgt_lang: Target language code (e.g. 'en' for English)
    '''
    # No translation needed if same language
    if src_lang == tgt_lang:
        return text

    # Lazy load models on first translation request
    global _translation_available
    if _translation_available is None:
        _load_indicTrans2()

    if not _translation_available:
        # Graceful fallback: return original text if model unavailable
        return text

    src_tag = LANG_MAP.get(src_lang)
    tgt_tag = LANG_MAP.get(tgt_lang)

    if not src_tag or not tgt_tag:
        logger.warning(f'Unsupported language pair: {src_lang} -> {tgt_lang}')
        return text

    try:
        # Choose correct pipeline direction
        if tgt_lang == 'en':
            return _run_translation(_indic_to_en, text, src_tag, tgt_tag)
        else:
            return _run_translation(_en_to_indic, text, src_tag, tgt_tag)
    except Exception as e:
        logger.error(f'Translation failed: {e}')
        return text  # Always return something usable


def query_to_english(query: str, src_lang: str) -> str:
    '''Convenience: translate a student question to English for the LLM'''
    return translate(query, src_lang=src_lang, tgt_lang='en')


def answer_to_language(answer: str, tgt_lang: str) -> str:
    '''Convenience: translate an English LLM answer to student's language'''
    return translate(answer, src_lang='en', tgt_lang=tgt_lang)