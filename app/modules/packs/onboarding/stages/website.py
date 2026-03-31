"""Website onboarding stage implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.onboarding.artifacts import build_website_blueprint


@dataclass(frozen=True)
class WebsiteStageRuntime:
    load_pack_and_job: Callable[[Session, UUID, str], tuple[Any | None, dict[str, Any] | None]]
    mark_stage: Callable[..., Any]
    log_job_event: Callable[..., Any]
    save_artifact: Callable[..., Any]
    merge_onboarding_answers: Callable[..., Any]
    compute_input_fingerprint: Callable[[Any], str]
    get_cached_fingerprint: Callable[[Any, str], str]
    has_generated_website_project: Callable[[Any], bool]
    default_builder_files: Callable[[], dict[str, str]]
    collect_stream_text: Callable[[Any], str]
    parse_generated_files: Callable[[str], dict[str, str]]
    parse_generation_summary: Callable[[str], str | None]
    text_or_none: Callable[..., str | None]
    iso_now: Callable[[], str]
    stage_name: str
    input_fingerprint_key: str
    auto_website_prompt: str
    default_builder_app_marker: str
    artifact_type: str


def run_website_stage(
    *,
    db: Session,
    pack_id: UUID,
    job_id: str,
    runtime: WebsiteStageRuntime,
):
    from app.modules.builder.generation import create_website_generation_stream
    from app.modules.builder.services import (
        create as create_builder_project,
        get_for_pack_any,
        update as update_builder_project,
    )
    from app.shared.generation_schemas import GenerationMessage
    from app.shared.services.generation_context import load_generation_brand_context

    pack, job = runtime.load_pack_and_job(db, pack_id, job_id)
    if not pack or not job:
        raise RuntimeError("Onboarding job is no longer available")
    stage = job["stages"][runtime.stage_name]
    input_fingerprint = runtime.compute_input_fingerprint(pack)
    project = get_for_pack_any(db, pack_id)

    if stage["status"] == "completed" or (
        project
        and runtime.has_generated_website_project(project)
        and runtime.get_cached_fingerprint(pack, runtime.input_fingerprint_key) == input_fingerprint
    ):
        if project:
            envelope = runtime.save_artifact(
                pack,
                runtime.artifact_type,
                build_website_blueprint(
                    project,
                    load_generation_brand_context(db, pack_id, pack=pack, artifacts_only=True),
                ),
                source_stage=runtime.stage_name,
                timestamp=runtime.iso_now(),
                job_id=job_id,
                input_fingerprint=input_fingerprint,
            )
            pack = runtime.merge_onboarding_answers(
                db,
                pack,
                {
                    "onboarding_website_project_id": str(project.id),
                    "onboarding_website_generated_at": runtime.iso_now(),
                    runtime.input_fingerprint_key: input_fingerprint,
                },
                commit=False,
            )
        return runtime.mark_stage(
            db,
            pack_id,
            job_id,
            runtime.stage_name,
            "completed",
            data={
                "project_id": str(project.id),
                "artifact_version": envelope.version,
            } if project else None,
        )

    runtime.mark_stage(db, pack_id, job_id, runtime.stage_name, "running")
    brand_context = load_generation_brand_context(db, pack_id, pack=pack, artifacts_only=True)
    if project is None:
        project_name = runtime.text_or_none(
            getattr(brand_context, "brand_name", None) or pack.name,
            limit=255,
        ) or "Website Project"
        project = create_builder_project(db, pack.created_by_user_id, pack.id, name=project_name)
        runtime.log_job_event(
            db,
            pack_id,
            job_id,
            f"Created website project {project.id}.",
            stage_name=runtime.stage_name,
        )

    current_files = dict(project.files or {}) or runtime.default_builder_files()
    runtime.log_job_event(
        db,
        pack_id,
        job_id,
        "Sending the first website draft request to the builder.",
        stage_name=runtime.stage_name,
    )
    generated_text = runtime.collect_stream_text(
        create_website_generation_stream(
            messages=[GenerationMessage(role="user", content=runtime.auto_website_prompt)],
            files=current_files,
            brand_context=brand_context,
            selected_style=None,
            assistant_mode="launch",
        )
    )
    generated_files = runtime.parse_generated_files(generated_text)
    if not generated_files:
        raise RuntimeError("Website generation did not produce any files")

    next_files = {**current_files, **generated_files}
    app_code = str(next_files.get("/App.tsx") or next_files.get("App.tsx") or "").strip()
    if not app_code or runtime.default_builder_app_marker in app_code:
        raise RuntimeError("Website generation did not produce a usable /App.tsx file")

    summary = runtime.parse_generation_summary(generated_text) or "Starter website ready."
    runtime.log_job_event(
        db,
        pack_id,
        job_id,
        f"Website generation returned {len(generated_files)} file(s).",
        stage_name=runtime.stage_name,
    )
    next_messages = list(project.messages or [])
    next_messages.extend(
        [
            {"role": "user", "content": runtime.auto_website_prompt},
            {"role": "assistant", "content": summary},
        ]
    )
    project = update_builder_project(
        db,
        project,
        files=next_files,
        messages=next_messages,
    )
    envelope = runtime.save_artifact(
        pack,
        runtime.artifact_type,
        build_website_blueprint(project, brand_context, summary=summary),
        source_stage=runtime.stage_name,
        timestamp=runtime.iso_now(),
        job_id=job_id,
        input_fingerprint=input_fingerprint,
    )
    pack = runtime.merge_onboarding_answers(
        db,
        pack,
        {
            "onboarding_website_project_id": str(project.id),
            "onboarding_website_generated_at": runtime.iso_now(),
            runtime.input_fingerprint_key: input_fingerprint,
        },
        commit=False,
    )
    return runtime.mark_stage(
        db,
        pack_id,
        job_id,
        runtime.stage_name,
        "completed",
        data={
            "project_id": str(project.id),
            "file_count": len(generated_files),
            "artifact_version": envelope.version,
        },
    )
