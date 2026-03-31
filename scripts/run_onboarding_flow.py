"""
Run the onboarding flow directly for a project without using HTTP.

Examples:
  python scripts/run_onboarding_flow.py <pack_id>
  python scripts/run_onboarding_flow.py <pack_id> --show-artifacts
  python scripts/run_onboarding_flow.py <pack_id> --status-only --show-artifacts
  python scripts/run_onboarding_flow.py <pack_id> --stage website
  python scripts/run_onboarding_flow.py <pack_id> --repair-from-qa
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.core.logging import set_logger_formatter_factory
from app.core.db.model_registry import load_model_metadata
from app.core.db.session import SessionLocal
from app.modules.packs.models import Pack
from app.modules.packs.onboarding import public as onboarding_public
from app.modules.packs.onboarding.constants import ONBOARDING_JOB_STAGES
from app.modules.packs.services import complete_onboarding, sync_pack_target_audience

load_model_metadata()

_STATUS_LABELS = {
    "completed": "[OK]",
    "running": "[RUN]",
    "failed": "[FAIL]",
    "skipped": "[SKIP]",
    "queued": "[QUEUE]",
    "paused": "[PAUSE]",
    "pending": "[....]",
    "not_started": "[....]",
}


class FriendlyCliLogFormatter(logging.Formatter):
    """Compact CLI-first log format for local onboarding runs."""

    default_time_format = "%H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.default_time_format)
        event = str(getattr(record, "event", "") or "").strip()
        if event == "service_call_start":
            service_name = _short_service_name(
                getattr(record, "service_module", record.name),
                getattr(record, "service_fn", record.funcName),
            )
            args = getattr(record, "service_args", None)
            if args:
                return f"[{timestamp}] CALL {service_name} | args={args}"
            return f"[{timestamp}] CALL {service_name}"
        if event == "service_call_ok":
            service_name = _short_service_name(
                getattr(record, "service_module", record.name),
                getattr(record, "service_fn", record.funcName),
            )
            return f"[{timestamp}] OK   {service_name} ({_format_duration_ms(getattr(record, 'duration_ms', None))})"
        if event == "service_call_error":
            service_name = _short_service_name(
                getattr(record, "service_module", record.name),
                getattr(record, "service_fn", record.funcName),
            )
            error = str(getattr(record, "error", "") or record.getMessage()).strip()
            return (
                f"[{timestamp}] FAIL {service_name} "
                f"({_format_duration_ms(getattr(record, 'duration_ms', None))}) | {error}"
            )

        level = record.levelname.upper().ljust(5)
        logger_name = _short_logger_name(record.name)
        message = _simplify_logger_message(logger_name, record.getMessage())
        return f"[{timestamp}] {level} {logger_name}: {message}"


def _log(message: str) -> None:
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, default=str), flush=True)


def _configure_cli_logging(*, raw_logs: bool = False) -> None:
    if raw_logs:
        set_logger_formatter_factory(None)
        return
    set_logger_formatter_factory(FriendlyCliLogFormatter)


def _status_summary(status_payload: dict[str, Any]) -> dict[str, Any]:
    stages = status_payload.get("stages") or {}
    stage_summary = {}
    if isinstance(stages, dict):
        for stage_name, stage_state in stages.items():
            if not isinstance(stage_state, dict):
                continue
            stage_summary[stage_name] = {
                "status": stage_state.get("status"),
                "started_at": stage_state.get("started_at"),
                "completed_at": stage_state.get("completed_at"),
                "last_error": stage_state.get("last_error"),
            }

    summary = {
        "status": status_payload.get("status"),
        "mode": status_payload.get("mode"),
        "job_id": status_payload.get("job_id"),
        "attempt": status_payload.get("attempt"),
        "max_attempts": status_payload.get("max_attempts"),
        "current_stage": status_payload.get("current_stage"),
        "requested_stage": status_payload.get("requested_stage"),
        "selected_stages": status_payload.get("selected_stages"),
        "last_error": status_payload.get("last_error"),
        "qa_overall_status": status_payload.get("qa_overall_status"),
        "qa_consistency_score": status_payload.get("qa_consistency_score"),
        "qa_recommended_repair_stage": status_payload.get("qa_recommended_repair_stage"),
        "qa_recommended_repair_reason": status_payload.get("qa_recommended_repair_reason"),
        "qa_auto_repairable": status_payload.get("qa_auto_repairable"),
        "stages": stage_summary,
    }
    return summary


def _format_duration_ms(value: Any) -> str:
    try:
        duration_ms = float(value)
    except (TypeError, ValueError):
        return "?"
    if duration_ms < 1000:
        return f"{duration_ms:.0f}ms"
    return f"{duration_ms / 1000:.2f}s"


def _short_logger_name(name: str) -> str:
    text = str(name or "").strip()
    if text.startswith("klarnow.services."):
        return text.removeprefix("klarnow.services.")
    if text.startswith("klarnow."):
        return text.removeprefix("klarnow.")
    return text or "app"


def _short_service_name(module: object, fn: object) -> str:
    module_text = str(module or "").strip()
    fn_text = str(fn or "").strip()
    if module_text.startswith("app.modules."):
        module_text = module_text.removeprefix("app.modules.")
    elif module_text.startswith("app."):
        module_text = module_text.removeprefix("app.")
    if fn_text and "." in fn_text and fn_text.split(".")[-1]:
        fn_text = fn_text.split(".")[-1]
    if module_text and fn_text:
        return f"{module_text}.{fn_text}"
    return fn_text or module_text or "service_call"


def _simplify_logger_message(logger_name: str, message: str) -> str:
    text = str(message or "").strip()
    prefixes = [f"{logger_name}: "]
    if "." in logger_name:
        prefixes.append(f"{logger_name.split('.')[-1]}: ")
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text


def _stage_status_label(status: object) -> str:
    return _STATUS_LABELS.get(str(status or "").strip().lower(), "[....]")


def _short_timestamp(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("T", " ").replace("Z", "")
    if "." in normalized:
        normalized = normalized.split(".", 1)[0]
    return normalized


def _format_summary_fields(payload: dict[str, Any]) -> str:
    return ", ".join(
        f"{key}={value}"
        for key, value in payload.items()
        if value not in (None, "", [], {}, False)
    )


def _ordered_stage_names(status_payload: dict[str, Any]) -> list[str]:
    stages = status_payload.get("stages")
    selected = status_payload.get("selected_stages")
    names: list[str] = []
    if isinstance(selected, list):
        names.extend(str(item).strip() for item in selected if str(item).strip())
    if isinstance(stages, dict):
        for stage_name in stages:
            normalized = str(stage_name).strip()
            if normalized and normalized not in names:
                names.append(normalized)
    return names


def _print_human_status(status_payload: dict[str, Any]) -> None:
    _log(
        "Job summary "
        f"| status={status_payload.get('status') or 'unknown'} "
        f"| mode={status_payload.get('mode') or 'full_run'} "
        f"| attempt={status_payload.get('attempt') or 0}/{status_payload.get('max_attempts') or 0} "
        f"| current_stage={status_payload.get('current_stage') or '-'}"
    )
    selected_stages = status_payload.get("selected_stages")
    if selected_stages:
        _log(f"Selected stages: {', '.join(str(item) for item in selected_stages)}")
    last_error = str(status_payload.get("last_error") or "").strip()
    if last_error:
        _log(f"Last error: {last_error}")

    qa_bits = []
    if status_payload.get("qa_overall_status"):
        qa_bits.append(f"overall={status_payload.get('qa_overall_status')}")
    if status_payload.get("qa_consistency_score") is not None:
        qa_bits.append(f"score={status_payload.get('qa_consistency_score')}")
    if status_payload.get("qa_recommended_repair_stage"):
        qa_bits.append(f"repair_stage={status_payload.get('qa_recommended_repair_stage')}")
    if status_payload.get("qa_auto_repairable") is not None:
        qa_bits.append(f"auto_repairable={bool(status_payload.get('qa_auto_repairable'))}")
    if qa_bits:
        _log("QA summary | " + " | ".join(qa_bits))
    qa_reason = str(status_payload.get("qa_recommended_repair_reason") or "").strip()
    if qa_reason:
        _log(f"QA repair reason: {qa_reason}")

    stages = status_payload.get("stages") or {}
    if not isinstance(stages, dict) or not stages:
        return
    _log("Stage results:")
    for stage_name in _ordered_stage_names(status_payload):
        stage_state = stages.get(stage_name) or {}
        status = str(stage_state.get("status") or "pending")
        line = f"  {_stage_status_label(status)} {stage_name}"
        started_at = _short_timestamp(stage_state.get("started_at"))
        completed_at = _short_timestamp(stage_state.get("completed_at"))
        if started_at:
            line += f" | started={started_at}"
        if completed_at:
            line += f" | completed={completed_at}"
        last_stage_error = str(stage_state.get("last_error") or "").strip()
        if last_stage_error:
            line += f" | error={last_stage_error}"
        print(line, flush=True)


def _print_human_events(events: list[dict[str, Any]], *, limit: int = 12) -> None:
    if not events:
        _log("Recent events: none")
        return
    visible_events = events[-limit:]
    _log(f"Recent events (showing {len(visible_events)} of {len(events)}):")
    for event in visible_events:
        timestamp = _short_timestamp(event.get("timestamp")) or "-"
        level = str(event.get("level") or "info").upper()
        stage = str(event.get("stage") or "-")
        message = str(event.get("message") or "").strip()
        print(f"  [{timestamp}] {level:<5} stage={stage:<16} {message}", flush=True)


def _print_human_artifacts(artifacts: list[dict[str, Any]]) -> None:
    if not artifacts:
        _log("Artifacts: none")
        return
    _log(f"Artifacts ({len(artifacts)}):")
    for artifact in artifacts:
        artifact_type = str(artifact.get("artifact_type") or "unknown")
        version = artifact.get("version")
        source_stage = str(artifact.get("source_stage") or "-")
        updated_at = _short_timestamp(artifact.get("updated_at")) or "-"
        summary = artifact.get("summary")
        line = f"  - {artifact_type} v{version} | stage={source_stage} | updated={updated_at}"
        if isinstance(summary, dict) and summary:
            line += f" | {_format_summary_fields(summary)}"
        print(line, flush=True)


def _load_pack_or_exit(db, pack_id: UUID) -> Pack:
    pack = db.get(Pack, pack_id)
    if not pack:
        print(f"Pack not found: {pack_id}", file=sys.stderr)
        raise SystemExit(1)
    return pack


def _print_pack_snapshot(pack: Pack) -> None:
    answers = pack.onboarding_answers or {}
    _log(
        "Loaded pack "
        f"{pack.id} | name={pack.name!r} | brand_name={pack.brand_name!r} "
        f"| onboarding_completed_at={pack.onboarding_completed_at} "
        f"| onboarding_background_completed_at={pack.onboarding_background_completed_at} "
        f"| has_existing_brand={answers.get('has_existing_brand')!r}"
    )


def _print_outputs(
    pack: Pack,
    *,
    show_events: bool,
    show_artifacts: bool,
    json_output: bool,
) -> None:
    status_payload = onboarding_public.get_onboarding_job_status(pack)
    if json_output:
        _log("Latest onboarding status:")
        _print_json(_status_summary(status_payload))
    else:
        _print_human_status(_status_summary(status_payload))
    if show_events:
        events = status_payload.get("events") or []
        if json_output:
            _log("Latest onboarding events:")
            _print_json(events)
        else:
            _print_human_events(events)
    if show_artifacts:
        artifacts = onboarding_public.get_onboarding_artifact_lineage(pack)
        if json_output:
            _log("Latest artifact lineage:")
            _print_json(artifacts)
        else:
            _print_human_artifacts(artifacts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the onboarding flow directly for a project without using HTTP.",
    )
    parser.add_argument("pack_id", help="Project UUID")
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Only print the latest onboarding status for the project.",
    )
    parser.add_argument(
        "--show-events",
        action="store_true",
        help="Print the stored onboarding event log after the run.",
    )
    parser.add_argument(
        "--show-artifacts",
        action="store_true",
        help="Print the latest typed artifact lineage after the run.",
    )
    parser.add_argument(
        "--skip-complete",
        action="store_true",
        help="Do not mark onboarding complete before enqueuing a full run.",
    )
    parser.add_argument(
        "--stage",
        help=(
            "Queue a bounded repair from a stage instead of a full run. "
            f"Internal stages: {', '.join(ONBOARDING_JOB_STAGES)}. "
            "Public stages like brand_identity, website, poster_flyers, and videos also work."
        ),
    )
    parser.add_argument(
        "--repair-from-qa",
        action="store_true",
        help="Queue the smallest recommended repair from the latest QA report.",
    )
    parser.add_argument(
        "--include-downstream",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include downstream stages when running a repair (default: true).",
    )
    parser.add_argument(
        "--reason",
        help="Optional reason to record on a repair job.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON status, events, and artifacts instead of the human-friendly summary.",
    )
    parser.add_argument(
        "--raw-logs",
        action="store_true",
        help="Keep the default application log format instead of the simplified CLI format.",
    )
    args = parser.parse_args()
    _configure_cli_logging(raw_logs=args.raw_logs)

    if args.stage and args.repair_from_qa:
        parser.error("Use either --stage or --repair-from-qa, not both.")

    try:
        pack_id = UUID(str(args.pack_id))
    except ValueError:
        print(f"Invalid pack id: {args.pack_id}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        pack = _load_pack_or_exit(db, pack_id)
        _print_pack_snapshot(pack)

        if args.status_only:
            _print_outputs(
                pack,
                show_events=args.show_events,
                show_artifacts=args.show_artifacts,
                json_output=args.json,
            )
            return 0

        if args.stage:
            _log(
                f"Queueing targeted repair from stage={args.stage!r} "
                f"| include_downstream={args.include_downstream}"
            )
            job = onboarding_public.enqueue_onboarding_stage_repair(
                db,
                pack_id,
                stage_name=args.stage,
                include_downstream=args.include_downstream,
                reason=args.reason,
            )
        elif args.repair_from_qa:
            _log(
                "Queueing QA-guided repair "
                f"| include_downstream={args.include_downstream}"
            )
            job = onboarding_public.enqueue_onboarding_qa_repair(
                db,
                pack_id,
                include_downstream=args.include_downstream,
                reason=args.reason,
            )
        else:
            sync_pack_target_audience(pack)
            if not args.skip_complete:
                complete_onboarding(db, pack, answers=pack.onboarding_answers or {}, commit=False)
            _log("Queueing full onboarding run")
            job = onboarding_public.enqueue_onboarding_job(db, pack_id)

        db.commit()
        db.refresh(pack)

        job_id = str(job.get("job_id") or "")
        if not job_id:
            print("Onboarding job did not return a job id.", file=sys.stderr)
            return 1

        _log(
            f"Running job synchronously | job_id={job_id} "
            f"| mode={job.get('mode') or 'full_run'}"
        )
        result = onboarding_public.run_onboarding_job(pack_id, job_id)
        while result.retry:
            _log(
                f"Retry requested after attempt={result.attempt}; "
                "running next attempt now..."
            )
            result = onboarding_public.run_onboarding_job(pack_id, job_id)

        db.expire_all()
        pack = _load_pack_or_exit(db, pack_id)
        _log(
            "Run finished "
            f"| retry={result.retry} | attempt={result.attempt} "
            f"| clear_dispatch={result.clear_dispatch}"
        )
        _print_outputs(
            pack,
            show_events=args.show_events,
            show_artifacts=args.show_artifacts,
            json_output=args.json,
        )
        return 0
    except Exception as exc:
        _log(f"Onboarding flow failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
