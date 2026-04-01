"""
Sentiment and tone alignment analysis.

Checks whether the emotional tone established in the Brand OS is preserved
in downstream agent outputs (identity, website, creative).

Demonstrates: NLP sentiment analysis (TextBlob polarity/subjectivity),
sentence-level tone inspection, tone drift measurement.
"""

from __future__ import annotations


def _ensure_nltk():
    import nltk
    for resource in ["punkt", "punkt_tab"]:
        try:
            nltk.data.find(f"tokenizers/{resource}")
        except LookupError:
            nltk.download(resource, quiet=True)


def analyse_sentiment(text: str) -> dict:
    """
    Analyse sentiment polarity and subjectivity using TextBlob.

    Returns:
        polarity: float in [-1.0, +1.0] (negative → positive)
        subjectivity: float in [0.0, 1.0] (objective → subjective)
    """
    from textblob import TextBlob

    blob = TextBlob(text or "")
    return {
        "polarity": round(blob.sentiment.polarity, 4),
        "subjectivity": round(blob.sentiment.subjectivity, 4),
    }


def tone_alignment(brand_os_text: str, output_text: str) -> dict:
    """
    Measure how well the tone of an output aligns with the Brand OS tone.

    A lower polarity/subjectivity difference = better tone alignment.
    Alignment scores are normalised to [0, 1] where 1 = perfect alignment.

    Args:
        brand_os_text: Reference Brand OS text.
        output_text: Downstream agent output to compare.

    Returns:
        Dict with raw sentiment values, per-dimension alignment, and overall score.
    """
    brand_s = analyse_sentiment(brand_os_text)
    output_s = analyse_sentiment(output_text)

    polarity_diff = abs(brand_s["polarity"] - output_s["polarity"])
    subjectivity_diff = abs(brand_s["subjectivity"] - output_s["subjectivity"])

    polarity_alignment = round(max(0.0, 1.0 - polarity_diff), 4)
    subjectivity_alignment = round(max(0.0, 1.0 - subjectivity_diff), 4)

    return {
        "brand_os_sentiment": brand_s,
        "output_sentiment": output_s,
        "polarity_alignment": polarity_alignment,
        "subjectivity_alignment": subjectivity_alignment,
        "overall_tone_alignment": round(
            (polarity_alignment + subjectivity_alignment) / 2, 4
        ),
    }


def sentence_level_sentiment(text: str) -> list[dict]:
    """
    Per-sentence sentiment analysis for detailed tone inspection.

    Useful for identifying exactly where tone drift occurs in a generated output.
    """
    _ensure_nltk()
    from nltk.tokenize import sent_tokenize

    return [
        {"sentence": sent[:120], **analyse_sentiment(sent)}
        for sent in sent_tokenize(text or "")
    ]
