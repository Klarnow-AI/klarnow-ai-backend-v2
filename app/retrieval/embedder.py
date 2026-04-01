"""
Sentence-BERT embedding module.

Uses the all-MiniLM-L6-v2 model — a distilled BERT model trained for
semantic textual similarity. Produces 384-dimensional dense vectors.

Demonstrates:
- Deep Learning: transformer-based embeddings (BERT architecture)
- Transfer Learning: pre-trained sentence-BERT applied to business text domain
- Cosine similarity for semantic comparison across agent outputs
"""

from __future__ import annotations

import numpy as np
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model() -> "SentenceTransformer":
    """Lazy-load the sentence-BERT model (cached singleton to save memory)."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Convert a list of text strings into dense vector embeddings.

    Args:
        texts: List of text strings to embed.

    Returns:
        numpy array of shape (len(texts), 384)
    """
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings  # type: ignore[return-value]


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot = np.dot(vec_a, vec_b)
    norm = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def pairwise_similarity(texts_a: list[str], texts_b: list[str]) -> np.ndarray:
    """
    Compute pairwise cosine similarity between two sets of texts.
    Useful for measuring cross-agent output consistency.

    Returns:
        Matrix of shape (len(texts_a), len(texts_b)) with cosine similarity scores.
    """
    emb_a = embed_texts(texts_a)
    emb_b = embed_texts(texts_b)

    norm_a = np.linalg.norm(emb_a, axis=1, keepdims=True)
    norm_b = np.linalg.norm(emb_b, axis=1, keepdims=True)
    emb_a = emb_a / np.where(norm_a == 0, 1, norm_a)
    emb_b = emb_b / np.where(norm_b == 0, 1, norm_b)

    return np.dot(emb_a, emb_b.T)
