"""
Scenarios router.

Serves the three pre-defined test scenarios used in the dissertation
evaluation. Used by the Flutter web app to populate the scenario picker.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/dissertation/scenarios", tags=["dissertation-scenarios"])

_SCENARIOS_DIR = Path("app/data/scenarios")


@router.get("/")
def list_scenarios():
    """List all available test scenarios (id, name, industry)."""
    scenarios = []
    if not _SCENARIOS_DIR.exists():
        return {"scenarios": scenarios}

    for f in sorted(_SCENARIOS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
            scenarios.append(
                {
                    "id": data["scenario_id"],
                    "name": data["scenario_name"],
                    "business_name": data["business_input"]["business_name"],
                    "industry": data["business_input"]["industry"],
                    "has_source_documents": bool(data.get("source_documents")),
                }
            )
        except Exception:
            continue

    return {"scenarios": scenarios}


@router.get("/{scenario_id}")
def get_scenario(scenario_id: str):
    """Return the full scenario JSON for a given scenario ID."""
    if not _SCENARIOS_DIR.exists():
        raise HTTPException(status_code=404, detail="Scenarios directory not found")

    matches = list(_SCENARIOS_DIR.glob(f"*{scenario_id}*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    try:
        return json.loads(matches[0].read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
