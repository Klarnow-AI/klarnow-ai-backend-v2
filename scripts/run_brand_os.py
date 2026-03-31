"""
Run Brand OS generation directly for a pack.

Examples:
  python scripts/run_brand_os.py <pack_id>
  python scripts/run_brand_os.py <pack_id> --allow-without-onboarding-complete
  python scripts/run_brand_os.py <pack_id> --show-full
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from uuid import UUID

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.core.db.model_registry import load_model_metadata
from app.core.db.session import SessionLocal
from app.modules.brand_os.schemas import brand_os_read_from_orm
from app.modules.brand_os.services import get_by_id_and_pack
from app.modules.brand_os.tools import generate_brand_os
from app.modules.packs.models import Pack

load_model_metadata()


def _log(message: str) -> None:
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def _build_summary(payload: dict) -> dict:
    foundation = payload.get("foundation") or {}
    strategy = payload.get("brand_strategy") or {}
    mission_vision = strategy.get("mission_vision") or {}
    positioning = strategy.get("positioning_differentiation") or {}
    voice = strategy.get("voice_personality") or {}
    return {
        "id": payload.get("id"),
        "pack_id": payload.get("pack_id"),
        "version": payload.get("version"),
        "brand_name": foundation.get("brand_name"),
        "one_line_offer": foundation.get("one_line_offer"),
        "main_audience": foundation.get("main_audience"),
        "mission": mission_vision.get("mission"),
        "vision": mission_vision.get("vision"),
        "promise": mission_vision.get("promise"),
        "positioning": positioning.get("statement"),
        "unique_advantage": positioning.get("unique_advantage"),
        "archetype": voice.get("archetype"),
        "voice_profile": voice.get("profile"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Brand OS generation directly for a pack.")
    parser.add_argument("pack_id", help="Pack UUID")
    parser.add_argument(
        "--source-job-id",
        help="Optional idempotency key to reuse an existing Brand OS created for the same job.",
    )
    parser.add_argument(
        "--allow-without-onboarding-complete",
        action="store_true",
        help="Bypass the onboarding-complete gate for new-brand packs.",
    )
    parser.add_argument(
        "--show-full",
        action="store_true",
        help="Print the full Brand OS JSON instead of a compact summary.",
    )
    args = parser.parse_args()

    try:
        pack_id = UUID(str(args.pack_id))
    except ValueError:
        print(f"Invalid pack id: {args.pack_id}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        pack = db.get(Pack, pack_id)
        if not pack:
            print(f"Pack not found: {pack_id}", file=sys.stderr)
            return 1

        answers = pack.onboarding_answers or {}
        _log(
            "Loaded pack "
            f"{pack_id} | name={pack.name!r} | brand_name={pack.brand_name!r} "
            f"| onboarding_completed_at={pack.onboarding_completed_at} "
            f"| has_existing_brand={answers.get('has_existing_brand')!r}"
        )
        _log("Starting Brand OS generation...")
        started_at = time.monotonic()
        result = generate_brand_os(
            db,
            pack_id,
            source_job_id=args.source_job_id,
            allow_without_onboarding_complete=args.allow_without_onboarding_complete,
            progress_callback=_log,
        )
        elapsed = time.monotonic() - started_at
        brand_os_id = UUID(str(result["brand_os_id"]))
        brand_os = get_by_id_and_pack(db, brand_os_id, pack_id)
        if not brand_os:
            print(
                "Brand OS generation returned an id, but the saved Brand OS row could not be loaded.",
                file=sys.stderr,
            )
            return 1

        payload = brand_os_read_from_orm(brand_os).model_dump(mode="json")
        _log(
            f"Brand OS completed in {elapsed:.2f}s | version={payload.get('version')} "
            f"| brand_os_id={payload.get('id')}"
        )
        print(
            json.dumps(payload if args.show_full else _build_summary(payload), indent=2),
            flush=True,
        )
        return 0
    except Exception as exc:
        _log(f"Brand OS generation failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
