"""
NLP text preprocessing module.

Demonstrates: tokenization, text cleaning, sentence segmentation,
chunking with overlap for context continuity.
"""

from __future__ import annotations

import re


def _ensure_nltk():
    import nltk
    for resource in ["punkt", "punkt_tab", "averaged_perceptron_tagger"]:
        try:
            nltk.data.find(f"tokenizers/{resource}")
        except LookupError:
            nltk.download(resource, quiet=True)


def clean_text(text: str) -> str:
    """Basic NLP text cleaning pipeline."""
    text = re.sub(r"\s+", " ", text)            # Normalise whitespace
    text = re.sub(r"[^\x00-\x7F]+", " ", text)  # Remove non-ASCII
    return text.strip()


def chunk_document(
    text: str,
    chunk_size: int = 400,
    overlap_sentences: int = 1,
) -> list[dict]:
    """
    Split a document into overlapping sentence-based chunks for embedding.

    Uses NLTK sentence tokenization for linguistically-aware splitting.
    Sentence overlap preserves context continuity at chunk boundaries.

    Args:
        text: Source document text.
        chunk_size: Target chunk size measured in word tokens.
        overlap_sentences: Number of trailing sentences to carry into the next chunk.

    Returns:
        List of dicts: {text, token_count, chunk_index}
    """
    _ensure_nltk()
    from nltk.tokenize import sent_tokenize, word_tokenize

    text = clean_text(text)
    sentences = sent_tokenize(text)

    chunks: list[dict] = []
    current_sentences: list[str] = []
    current_tokens = 0
    chunk_index = 0

    for sentence in sentences:
        sentence_tokens = len(word_tokenize(sentence))

        if current_tokens + sentence_tokens > chunk_size and current_sentences:
            chunks.append(
                {
                    "text": " ".join(current_sentences),
                    "token_count": current_tokens,
                    "chunk_index": chunk_index,
                }
            )
            chunk_index += 1

            overlap = current_sentences[-overlap_sentences:] if overlap_sentences > 0 else []
            current_sentences = overlap
            current_tokens = sum(len(word_tokenize(s)) for s in overlap)

        current_sentences.append(sentence)
        current_tokens += sentence_tokens

    if current_sentences:
        chunks.append(
            {
                "text": " ".join(current_sentences),
                "token_count": current_tokens,
                "chunk_index": chunk_index,
            }
        )

    return chunks


def extract_entities_simple(text: str) -> dict:
    """
    Lightweight entity/keyword extraction for EDA.
    Extracts capitalised multi-word phrases as candidate named entities.
    """
    _ensure_nltk()
    from nltk.tokenize import word_tokenize

    words = word_tokenize(text)
    entities: list[str] = []
    current_entity: list[str] = []

    for word in words:
        if word[0].isupper() and word.isalpha():
            current_entity.append(word)
        else:
            if len(current_entity) > 1:
                entities.append(" ".join(current_entity))
            current_entity = []

    alpha_words = [w for w in words if w.isalpha()]
    unique_lower = set(w.lower() for w in alpha_words)

    return {
        "total_words": len(words),
        "unique_words": len(unique_lower),
        "potential_entities": list(set(entities)),
        "vocabulary_richness": round(
            len(unique_lower) / max(len(alpha_words), 1), 4
        ),
    }
