"""
Semantic similarity evaluation using sentence-BERT embeddings.

Measures cross-agent consistency by comparing Brand OS embeddings
with downstream output embeddings (identity, website, creative).

Demonstrates: BERT-based deep learning evaluation, cosine similarity
as a consistency metric in a multi-agent generative system.
"""

from __future__ import annotations

import numpy as np

from app.retrieval.embedder import embed_texts, cosine_similarity


def measure_brand_os_consistency(brand_os_text: str, outputs: dict[str, str]) -> dict:
    """
    Measure semantic similarity between Brand OS and each downstream agent output.

    A higher score indicates that the downstream output preserves the semantic
    intent of the Brand OS — a proxy for multi-agent consistency.

    Args:
        brand_os_text: The generated Brand OS text.
        outputs: Dict mapping output_type -> generated text.

    Returns:
        Dict with per-output similarity scores and an average.
    """
    if not brand_os_text.strip():
        return {"error": "brand_os_text is empty"}

    brand_embedding = embed_texts([brand_os_text])[0]

    results: dict = {}
    scores: list[float] = []

    for output_type, output_text in outputs.items():
        if not (output_text or "").strip():
            continue
        output_embedding = embed_texts([output_text])[0]
        score = cosine_similarity(brand_embedding, output_embedding)
        results[output_type] = {
            "similarity_score": round(score, 4),
            "interpretation": _interpret_similarity(score),
        }
        scores.append(score)

    if scores:
        results["average_consistency"] = round(float(np.mean(scores)), 4)

    return results


def _interpret_similarity(score: float) -> str:
    if score >= 0.80:
        return "Very high consistency"
    elif score >= 0.60:
        return "Good consistency"
    elif score >= 0.40:
        return "Moderate consistency"
    elif score >= 0.20:
        return "Weak consistency"
    else:
        return "Very low consistency"


def cross_output_consistency(outputs: dict[str, str]) -> dict:
    """
    Compute pairwise semantic similarity between all agent outputs.

    Returns a flat dict of {type_a_vs_type_b: score} for every pair.
    Useful for detecting where semantic drift enters the pipeline.
    """
    output_types = [k for k, v in outputs.items() if (v or "").strip()]
    if len(output_types) < 2:
        return {}

    texts = [outputs[k] for k in output_types]
    embeddings = embed_texts(texts).astype("float32")

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    embeddings = embeddings / norms
    similarity_matrix = np.dot(embeddings, embeddings.T)

    results: dict = {}
    for i, type_a in enumerate(output_types):
        for j, type_b in enumerate(output_types):
            if i < j:
                key = f"{type_a}_vs_{type_b}"
                results[key] = round(float(similarity_matrix[i][j]), 4)

    return results
