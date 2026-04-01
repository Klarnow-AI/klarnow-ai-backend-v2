"""
Dissertation pipeline router.

Exposes endpoints to run the 6-agent dissertation pipeline on a scenario,
with or without retrieval grounding. Saves outputs for the evaluation pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/dissertation/pipeline", tags=["dissertation-pipeline"])

_SCENARIOS_DIR = Path("app/data/scenarios")
_OUTPUTS_DIR = Path("app/data/outputs")

# -----------------------------------------------------------------------
# Request / response schemas
# -----------------------------------------------------------------------

class PipelineRunRequest(BaseModel):
    scenario_id: str
    use_retrieval: bool = False


class PipelineRunResponse(BaseModel):
    scenario_id: str
    variant: str
    status: str
    output: dict | None = None
    error: str | None = None


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _load_scenario(scenario_id: str) -> dict:
    if not _SCENARIOS_DIR.exists():
        raise HTTPException(status_code=404, detail="Scenarios directory not found")
    matches = list(_SCENARIOS_DIR.glob(f"*{scenario_id}*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return json.loads(matches[0].read_text())


def _load_saved_output(scenario_id: str, variant: str) -> dict | None:
    path = _OUTPUTS_DIR / variant / f"{scenario_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


# -----------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------

@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(request: PipelineRunRequest):
    """
    Run the multi-agent dissertation pipeline.

    Set use_retrieval=false for the baseline variant (no RAG).
    Set use_retrieval=true for the grounded variant (sentence-BERT + FAISS RAG).
    Results are saved to disk and returned in the response.
    """
    from app.dissertation.pipeline import run_dissertation_pipeline

    scenario = _load_scenario(request.scenario_id)
    variant = "grounded" if request.use_retrieval else "baseline"

    try:
        output = await run_dissertation_pipeline(
            scenario=scenario,
            use_retrieval=request.use_retrieval,
        )
        return PipelineRunResponse(
            scenario_id=request.scenario_id,
            variant=variant,
            status="completed",
            output=output.model_dump(),
        )
    except Exception as e:
        return PipelineRunResponse(
            scenario_id=request.scenario_id,
            variant=variant,
            status="failed",
            error=str(e),
        )


@router.get("/outputs/{scenario_id}")
def get_outputs(scenario_id: str):
    """
    Return saved pipeline outputs for a scenario.

    Returns both variants (baseline + grounded) if available.
    """
    result: dict = {"scenario_id": scenario_id}
    for variant in ("baseline", "grounded"):
        saved = _load_saved_output(scenario_id, variant)
        result[variant] = saved
    return result


@router.get("/outputs/{scenario_id}/{variant}")
def get_variant_output(scenario_id: str, variant: str):
    """Return saved pipeline output for a specific scenario + variant."""
    if variant not in ("baseline", "grounded"):
        raise HTTPException(status_code=400, detail="variant must be 'baseline' or 'grounded'")
    saved = _load_saved_output(scenario_id, variant)
    if saved is None:
        raise HTTPException(
            status_code=404,
            detail=f"No saved output for scenario='{scenario_id}', variant='{variant}'. "
                   f"Run the pipeline first via POST /api/dissertation/pipeline/run",
        )
    return saved
