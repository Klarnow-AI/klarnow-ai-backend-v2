"""
Evaluation router.

Exposes endpoints to run the NLP evaluation pipeline on saved pipeline outputs,
compare baseline vs grounded variants, and analyse individual texts.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/dissertation/evaluation", tags=["dissertation-evaluation"])


# -----------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------

@router.get("/run/{scenario_name}")
def run_scenario_evaluation(scenario_name: str):
    """
    Run the full NLP evaluation for one scenario (baseline vs grounded).

    Requires that both baseline and grounded outputs have been saved via
    the pipeline endpoint first.
    """
    from app.evaluation.run_evaluation import evaluate_scenario

    try:
        return evaluate_scenario(scenario_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run-all")
def run_all_evaluations():
    """
    Run evaluation across all three scenarios.

    Skips scenarios where outputs are not yet saved.
    Also exports a CSV to evaluation_results/results.csv.
    """
    from app.evaluation.run_evaluation import evaluate_scenario, export_results_csv

    scenarios = ["freshclean", "glowbotanics", "databridge"]
    results = []
    skipped = []

    for s in scenarios:
        try:
            results.append(evaluate_scenario(s))
        except FileNotFoundError:
            skipped.append(s)

    csv_path = None
    if results:
        csv_path = export_results_csv(results)

    return {
        "evaluated": [r["scenario"] for r in results],
        "skipped": skipped,
        "csv_path": csv_path,
        "results": results,
    }


class AnalyseTextRequest(BaseModel):
    text: str
    reference_text: str | None = None


@router.post("/analyse-text")
def analyse_text(request: AnalyseTextRequest):
    """
    Analyse a single text with all NLP metrics.

    Optionally provide a reference_text to compute tone alignment and
    semantic similarity against (e.g. use Brand OS as reference).
    """
    from app.evaluation.text_statistics import compute_statistics, word_frequency_analysis
    from app.evaluation.sentiment_analysis import analyse_sentiment, sentence_level_sentiment

    result: dict = {
        "statistics": compute_statistics(request.text),
        "sentiment": analyse_sentiment(request.text),
        "top_words": word_frequency_analysis(request.text, top_n=15),
        "sentence_sentiments": sentence_level_sentiment(request.text),
    }

    if request.reference_text:
        from app.evaluation.semantic_similarity import measure_brand_os_consistency
        from app.evaluation.sentiment_analysis import tone_alignment

        result["semantic_similarity_to_reference"] = measure_brand_os_consistency(
            request.reference_text, {"target": request.text}
        ).get("target", {})
        result["tone_alignment_to_reference"] = tone_alignment(
            request.reference_text, request.text
        )

    return result


@router.get("/consistency/{scenario_name}/{variant}")
def measure_consistency(scenario_name: str, variant: str):
    """
    Measure cross-agent semantic consistency for a specific saved output.

    Returns Brand OS → downstream similarity scores and pairwise matrix.
    """
    import json
    from pathlib import Path
    from app.evaluation.semantic_similarity import (
        measure_brand_os_consistency,
        cross_output_consistency,
    )
    from app.evaluation.run_evaluation import _extract_text

    if variant not in ("baseline", "grounded"):
        raise HTTPException(status_code=400, detail="variant must be 'baseline' or 'grounded'")

    path = Path("app/data/outputs") / variant / f"{scenario_name}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No output at {path}")

    outputs = json.loads(path.read_text())
    brand_os_text = _extract_text(outputs.get("brand_os", {}))

    downstream = {
        key: _extract_text(outputs.get(key, {}))
        for key in ("identity", "website", "creative")
        if outputs.get(key)
    }

    return {
        "scenario": scenario_name,
        "variant": variant,
        "brand_os_vs_downstream": measure_brand_os_consistency(brand_os_text, downstream),
        "cross_output_pairwise": cross_output_consistency(
            {"brand_os": brand_os_text, **downstream}
        ),
    }
