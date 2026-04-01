"""
Text statistical analysis for EDA and output comparison.

Demonstrates: tokenization, feature extraction, vocabulary richness,
readability proxies — standard NLP data science skills.
"""

from __future__ import annotations

from collections import Counter


def _ensure_nltk():
    import nltk
    for resource in ["punkt", "punkt_tab"]:
        try:
            nltk.data.find(f"tokenizers/{resource}")
        except LookupError:
            nltk.download(resource, quiet=True)


_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "and", "but", "or",
    "nor", "not", "so", "yet", "both", "either", "neither", "each",
    "every", "all", "any", "few", "more", "most", "other", "some",
    "such", "no", "only", "own", "same", "than", "too", "very", "just",
    "because", "if", "when", "while", "where", "how", "what", "which",
    "who", "whom", "this", "that", "these", "those", "i", "me", "my",
    "we", "our", "you", "your", "he", "him", "his", "she", "her", "it",
    "its", "they", "them", "their",
})


def compute_statistics(text: str) -> dict:
    """Compute comprehensive text statistics for a generated output."""
    _ensure_nltk()
    from nltk.tokenize import word_tokenize, sent_tokenize

    text = text or ""
    words = word_tokenize(text)
    sentences = sent_tokenize(text)
    alpha_words = [w.lower() for w in words if w.isalpha()]

    word_lengths = [len(w) for w in alpha_words]
    sent_lengths = [len(word_tokenize(s)) for s in sentences]

    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "unique_words": len(set(alpha_words)),
        "vocabulary_richness": round(
            len(set(alpha_words)) / max(len(alpha_words), 1), 4
        ),
        "avg_word_length": round(
            sum(word_lengths) / max(len(word_lengths), 1), 2
        ),
        "avg_sentence_length": round(
            sum(sent_lengths) / max(len(sent_lengths), 1), 2
        ),
        "max_sentence_length": max(sent_lengths) if sent_lengths else 0,
        "min_sentence_length": min(sent_lengths) if sent_lengths else 0,
    }


def compare_statistics(baseline_text: str, grounded_text: str) -> dict:
    """
    Compare text statistics between baseline (no RAG) and grounded (RAG) outputs.

    Returns per-metric dict with {baseline, grounded, difference}.
    """
    baseline = compute_statistics(baseline_text)
    grounded = compute_statistics(grounded_text)

    return {
        key: {
            "baseline": baseline[key],
            "grounded": grounded[key],
            "difference": round(grounded[key] - baseline[key], 4)
            if isinstance(baseline[key], (int, float))
            else None,
        }
        for key in baseline
    }


def word_frequency_analysis(text: str, top_n: int = 20) -> list[dict]:
    """Top-N content word frequencies (excluding stopwords)."""
    _ensure_nltk()
    from nltk.tokenize import word_tokenize

    words = word_tokenize((text or "").lower())
    filtered = [
        w for w in words
        if w.isalpha() and w not in _STOPWORDS and len(w) > 2
    ]
    counter = Counter(filtered)
    return [{"word": w, "count": c} for w, c in counter.most_common(top_n)]
