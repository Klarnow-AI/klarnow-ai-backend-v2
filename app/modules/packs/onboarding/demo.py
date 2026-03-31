"""Helpers for running the onboarding flow end-to-end from local scripts or notebooks."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.modules.packs.models import Pack, User
from app.modules.packs.onboarding import public as onboarding_public
from app.modules.packs.services import (
    complete_onboarding,
    create_pack,
    submit_onboarding,
    sync_pack_target_audience,
)


def _default_demo_email() -> str:
    return f"onboarding-demo-{int(time.time())}-{uuid4().hex[:8]}@example.com"


def _default_demo_answers(brand_name: str) -> dict[str, Any]:
    return {
        "pack_type": "enquiries",
        "has_existing_brand": "no",
        "brand_name": brand_name,
        "what_do_you_do": (
            "We help early-stage service businesses clarify their offer, tighten their messaging, "
            "and launch a conversion-focused online presence fast."
        ),
        "why_started": (
            "We saw too many great small businesses struggle to explain their value clearly, "
            "so we built a faster way to turn raw expertise into a launch-ready brand."
        ),
        "who_are_your_customers": (
            "Founder-led service businesses that need clearer positioning, stronger messaging, "
            "and better conversion assets without hiring a full agency."
        ),
        "primary_cta": "Book a strategy call",
        "proof_text": (
            "We have helped dozens of service businesses sharpen their positioning and go live "
            "with clearer messaging and better conversion pages."
        ),
        "vibe_chips": ["bold", "modern", "clear", "premium"],
    }


@dataclass(slots=True)
class DemoProjectSpec:
    project_name: str = "Onboarding Demo Project"
    brand_name: str = "Northstar Launch Studio"
    owner_email: str = field(default_factory=_default_demo_email)
    owner_password_hash: str = "not-for-login"
    pack_type: str = "enquiries"
    has_existing_brand: bool = False
    brand_url: str | None = None
    onboarding_answers: dict[str, Any] | None = None

    def build_answers(self) -> dict[str, Any]:
        answers = dict(self.onboarding_answers or _default_demo_answers(self.brand_name))
        answers["pack_type"] = self.pack_type
        answers["brand_name"] = str(answers.get("brand_name") or self.brand_name).strip() or self.brand_name
        if self.has_existing_brand:
            answers["has_existing_brand"] = "yes"
            answers["brand_url"] = (
                str(self.brand_url or answers.get("brand_url") or "https://example.com").strip()
            )
            answers.pop("vibe_chips", None)
        else:
            answers["has_existing_brand"] = "no"
            if not answers.get("vibe_chips"):
                answers["vibe_chips"] = ["bold", "modern", "clear", "premium"]
        return answers


def _get_or_create_demo_user(db: Session, email: str, password_hash: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(email=email, hashed_password=password_hash)
    db.add(user)
    db.flush()
    return user


def _project_snapshot(project: Pack) -> dict[str, Any]:
    return {
        "project_id": str(project.id),
        "project_name": project.name,
        "brand_name": project.brand_name,
        "status": project.status,
        "pack_type": project.pack_type,
        "onboarding_completed_at": project.onboarding_completed_at,
        "onboarding_background_completed_at": project.onboarding_background_completed_at,
    }


def _status_summary(status_payload: dict[str, Any]) -> dict[str, Any]:
    stages = status_payload.get("stages") or {}
    summarized_stages: dict[str, Any] = {}
    if isinstance(stages, dict):
        for stage_name, stage_state in stages.items():
            if not isinstance(stage_state, dict):
                continue
            summarized_stages[stage_name] = {
                "status": stage_state.get("status"),
                "started_at": stage_state.get("started_at"),
                "completed_at": stage_state.get("completed_at"),
                "last_error": stage_state.get("last_error"),
            }
    return {
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
        "stages": summarized_stages,
    }


def run_demo_project_flow(db: Session, spec: DemoProjectSpec) -> dict[str, Any]:
    """Create a demo user + project, submit onboarding, and run the full flow synchronously."""
    user = _get_or_create_demo_user(db, spec.owner_email, spec.owner_password_hash)
    project = create_pack(
        db,
        user.id,
        name=spec.project_name,
        pack_type=spec.pack_type,
        commit=False,
    )
    project = submit_onboarding(db, project, spec.build_answers())
    sync_pack_target_audience(project)
    complete_onboarding(db, project, answers=project.onboarding_answers or {}, commit=False)
    job = onboarding_public.enqueue_onboarding_job(db, project.id)
    db.commit()
    db.refresh(project)

    job_id = str(job.get("job_id") or "")
    if not job_id:
        raise RuntimeError("Onboarding job did not return a job id.")

    run_result = onboarding_public.run_onboarding_job(project.id, job_id)
    while run_result.retry:
        run_result = onboarding_public.run_onboarding_job(project.id, job_id)

    db.expire_all()
    project = db.get(Pack, project.id)
    if not project:
        raise RuntimeError("The demo project could not be reloaded after the onboarding run.")

    status_payload = onboarding_public.get_onboarding_job_status(project)
    artifacts = onboarding_public.get_onboarding_artifact_lineage(project)

    return {
        "owner_email": user.email,
        "project": _project_snapshot(project),
        "status": _status_summary(status_payload),
        "events": status_payload.get("events") or [],
        "artifacts": artifacts,
        "job_result": {
            "retry": run_result.retry,
            "attempt": run_result.attempt,
            "clear_dispatch": run_result.clear_dispatch,
        },
    }
