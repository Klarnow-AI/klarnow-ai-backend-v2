"""
Main evaluation runner.

Loads saved pipeline outputs for baseline and grounded variants,
runs all NLP metrics, and exports results to CSV for dissertation tables.

Usage:
    python -m app.evaluation.run_evaluation
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path

from app.evaluation.semantic_similarity import (
    measure_brand_os_consistency,
    cross_output_consistency,
)
from app.evaluation.sentiment_analysis import tone_alignment
from app.evaluation.text_statistics import compute_statistics


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _extract_text(obj) -> str:
    """Recursively extract text content from a nested output object."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        for key in ("text", "content", "output", "result", "body", "copy", "description"):
            if key in obj:
                return _extract_text(obj[key])
        return " ".join(str(v) for v in obj.values() if isinstance(v, str))
    if isinstance(obj, list):
        return " ".join(_extract_text(item) for item in obj)
    return str(obj) if obj else ""


def load_outputs(scenario_name: str, variant: str, data_dir: str = "app/data/outputs") -> dict:
    path = Path(data_dir) / variant / f"{scenario_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"No saved outputs at {path}")
    with open(path) as f:
        return json.load(f)


# ------------------------------------------------------------------
# Per-scenario evaluation
# ------------------------------------------------------------------

def evaluate_scenario(scenario_name: str, data_dir: str = "app/data/outputs") -> dict:
    """
    Run the full evaluation suite for one scenario (baseline vs grounded).

    Returns a dict with per-variant metrics for semantic similarity,
    tone alignment, and text statistics.
    """
    baseline = load_outputs(scenario_name, "baseline", data_dir)
    grounded = load_outputs(scenario_name, "grounded", data_dir)

    result: dict = {
        "scenario": scenario_name,
        "timestamp": datetime.now().isoformat(),
    }

    for variant_name, outputs in [("baseline", baseline), ("grounded", grounded)]:
        brand_os_text = _extract_text(outputs.get("brand_os", {}))

        downstream: dict[str, str] = {}
        for key in ("identity", "website", "creative"):
            text = _extract_text(outputs.get(key, {}))
            if text.strip():
                downstream[key] = text

        # Semantic similarity (sentence-BERT)
        consistency = measure_brand_os_consistency(brand_os_text, downstream)

        # Cross-output pairwise consistency
        cross = cross_output_consistency({"brand_os": brand_os_text, **downstream})

        # Tone alignment (TextBlob)
        tone: dict = {}
        for key, text in downstream.items():
            tone[key] = tone_alignment(brand_os_text, text)

        # Text statistics (tokenization-based)
        stats: dict = {"brand_os": compute_statistics(brand_os_text)}
        for key, text in downstream.items():
            stats[key] = compute_statistics(text)

        result[variant_name] = {
            "consistency": consistency,
            "cross_consistency": cross,
            "tone_alignment": tone,
            "text_statistics": stats,
        }

    return result


# ------------------------------------------------------------------
# CSV export
# ------------------------------------------------------------------

def export_results_csv(
    all_results: list[dict],
    output_path: str = "evaluation_results/results.csv",
) -> str:
    """Export evaluation results to CSV for dissertation tables."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rows: list[dict] = []
    for result in all_results:
        scenario = result["scenario"]
        for variant in ("baseline", "grounded"):
            data = result.get(variant, {})
            consistency = data.get("consistency", {})
            for output_type in ("identity", "website", "creative"):
                cons = consistency.get(output_type, {})
                tone = data.get("tone_alignment", {}).get(output_type, {})
                stats = data.get("text_statistics", {}).get(output_type, {})
                rows.append(
                    {
                        "scenario": scenario,
                        "variant": variant,
                        "output_type": output_type,
                        "semantic_similarity": cons.get("similarity_score", ""),
                        "tone_alignment": tone.get("overall_tone_alignment", ""),
                        "word_count": stats.get("word_count", ""),
                        "vocabulary_richness": stats.get("vocabulary_richness", ""),
                        "avg_sentence_length": stats.get("avg_sentence_length", ""),
                    }
                )

    if rows:
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    return output_path


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    scenarios = ["freshclean", "glowbotanics", "databridge"]
    all_results: list[dict] = []

    for scenario in scenarios:
        try:
            result = evaluate_scenario(scenario)
            all_results.append(result)
            print(f"[OK] Evaluated: {scenario}")
        except FileNotFoundError as e:
            print(f"[SKIP] {scenario}: {e}")

    if not all_results:
        print("No outputs found. Run the pipeline on at least one scenario first.")
        return

    csv_path = export_results_csv(all_results)
    print(f"\nCSV exported to: {csv_path}")

    json_path = "evaluation_results/full_results.json"
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Full JSON results: {json_path}")


if __name__ == "__main__":
    main()
