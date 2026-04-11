"""
Create a fresh demo pack and run the onboarding flow end-to-end without HTTP.

Examples:
  python scripts/run_onboarding_demo.py
  python scripts/run_onboarding_demo.py --show-artifacts
  python scripts/run_onboarding_demo.py --pack-name "My Demo" --brand-name "Acme Studio"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.core.db.model_registry import load_model_metadata
from app.core.db.session import SessionLocal
from app.modules.packs.onboarding.demo import DemoProjectSpec, run_demo_project_flow

load_model_metadata()


def _print_json(payload) -> None:
    print(json.dumps(payload, indent=2, default=str), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a fresh demo pack and run the onboarding flow end-to-end.",
    )
    parser.add_argument("--pack-name", default="Onboarding Demo Project")
    parser.add_argument("--brand-name", default="Northstar Launch Studio")
    parser.add_argument("--owner-email", help="Optional email for the generated demo owner.")
    parser.add_argument(
        "--existing-brand",
        action="store_true",
        help="Use the existing-brand path instead of the new-brand path.",
    )
    parser.add_argument(
        "--brand-url",
        help="Optional website URL for existing-brand runs.",
    )
    parser.add_argument(
        "--show-events",
        action="store_true",
        help="Print stored onboarding events.",
    )
    parser.add_argument(
        "--show-artifacts",
        action="store_true",
        help="Print typed artifact lineage.",
    )
    args = parser.parse_args()

    spec = DemoProjectSpec(
        project_name=args.project_name,
        brand_name=args.brand_name,
        owner_email=args.owner_email or DemoProjectSpec().owner_email,
        has_existing_brand=bool(args.existing_brand),
        brand_url=args.brand_url,
    )

    with SessionLocal() as db:
        result = run_demo_project_flow(db, spec)

    _print_json(
        {
            "owner_email": result["owner_email"],
            "pack": result["pack"],
            "job_result": result["job_result"],
            "status": result["status"],
        }
    )
    if args.show_events:
        _print_json({"events": result["events"]})
    if args.show_artifacts:
        _print_json({"artifacts": result["artifacts"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
