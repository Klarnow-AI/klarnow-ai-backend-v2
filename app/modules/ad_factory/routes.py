"""Ad Factory V2.1 API routes."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.exc import DBAPIError, OperationalError

from app.core.auth.deps import get_current_user
from app.core.db.session import get_db
from app.core.errors import (
    NotFoundError,
    ServiceUnavailableError,
    map_value_error_to_app_error,
)
from app.modules.ad_factory.render_service import create_render_job, read_render_job
from app.modules.ad_factory.schemas import (
    AdFactoryCompileRead,
    AdFactoryLaunchResponse,
    AdFactoryRenderJobRead,
    LegacyGenerateResponse,
)
from app.modules.ad_factory.services import (
    build_legacy_generate_response,
    generate_compile,
    mark_variant_live,
    read_compile,
)
from app.modules.packs.models import User

router = APIRouter()
_TRANSIENT_DB_ERROR_MARKERS = (
    "ssl error",
    "server closed the connection unexpectedly",
    "connection not open",
    "connection reset by peer",
    "could not receive data from server",
    "terminating connection due to administrator command",
)


def _is_transient_db_connection_error(exc: Exception) -> bool:
    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_DB_ERROR_MARKERS)


class GenerateBody(BaseModel):
    pack_id: UUID
    selection_seed: str | None = Field(None, min_length=16, max_length=128)


class LegacyRenderBody(BaseModel):
    variant_slots: list[str] = Field(..., min_length=1, max_length=3)


class RenderJobBody(BaseModel):
    compile_result_id: UUID
    selected_variants: list[str] = Field(..., min_length=1, max_length=3)
    durations_requested: list[int] = Field(default_factory=lambda: [30], min_length=1, max_length=2)
    voiceover_addon: bool = False
    provider_target: str = "kling"
    idempotency_key: str | None = Field(None, min_length=8, max_length=128)


@router.post("/compiles", response_model=AdFactoryCompileRead)
def post_compile(
    body: GenerateBody,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return generate_compile(
            db,
            body.pack_id,
            current_user.id,
            selection_seed=body.selection_seed,
        )
    except ValueError as exc:
        raise map_value_error_to_app_error(exc) from exc
    except OperationalError as exc:
        try:
            db.rollback()
        except Exception:
            pass
        if _is_transient_db_connection_error(exc):
            raise ServiceUnavailableError(
                "Database connection dropped while saving Ad Factory compile output. Please retry."
            ) from exc
        raise


@router.get("/compiles/{compile_id}", response_model=AdFactoryCompileRead)
def get_compile_by_id(
    compile_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    compile_read = read_compile(db, compile_id, current_user.id)
    if not compile_read:
        raise NotFoundError("Compile result not found")
    return compile_read


@router.post("/renders", response_model=AdFactoryRenderJobRead)
def post_render_job(
    body: RenderJobBody,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return create_render_job(
            db,
            compile_id=body.compile_result_id,
            user_id=current_user.id,
            selected_variants=body.selected_variants,
            durations_requested=body.durations_requested,
            voiceover_addon=body.voiceover_addon,
            provider_target=body.provider_target,
            idempotency_key=body.idempotency_key,
            background_tasks=background_tasks,
        )
    except ValueError as exc:
        raise map_value_error_to_app_error(exc) from exc


@router.get("/renders/{render_job_id}", response_model=AdFactoryRenderJobRead)
def get_render_job_by_id(
    render_job_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    render_job = read_render_job(db, render_job_id, current_user.id)
    if not render_job:
        raise NotFoundError("Render job not found")
    return render_job


@router.post("/compiles/{compile_id}/launches/{slot}", response_model=AdFactoryLaunchResponse)
def post_launch_variant(
    compile_id: UUID,
    slot: str,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return mark_variant_live(db, compile_id, current_user.id, slot)
    except ValueError as exc:
        raise map_value_error_to_app_error(exc) from exc


@router.post("/generate", response_model=LegacyGenerateResponse)
def legacy_generate(
    body: GenerateBody,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    compile_read = post_compile(body, db=db, current_user=current_user)
    return build_legacy_generate_response(compile_read)


@router.post("/renders/{compile_id}/render", response_model=dict)
def legacy_render(
    compile_id: UUID,
    body: LegacyRenderBody,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        render_job = create_render_job(
            db,
            compile_id=compile_id,
            user_id=current_user.id,
            selected_variants=body.variant_slots,
            durations_requested=[30],
            voiceover_addon=False,
            provider_target="kling",
            background_tasks=background_tasks,
        )
    except ValueError as exc:
        raise map_value_error_to_app_error(exc) from exc
    render_result = dict(render_job.render_result)
    return {
        "asset_ids": render_result.get("asset_ids", []),
        "assets": render_result.get("assets", []),
        "render_job_id": str(render_job.id),
    }


@router.get("/legacy/renders/{compile_id}", response_model=dict)
def legacy_get_compile_as_render(
    compile_id: UUID,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    compile_read = read_compile(db, compile_id, current_user.id)
    if not compile_read:
        raise NotFoundError("Render not found")
    return {
        "render_id": str(compile_read.id),
        "pack_id": str(compile_read.pack_id),
        "status": compile_read.status,
        "brand_brief": compile_read.brand_brief.model_dump(mode="json"),
        "pack_snapshot": compile_read.pack_snapshot.model_dump(mode="json"),
        "variants": [variant.model_dump(mode="json") for variant in compile_read.compile_result.variants.as_dict().values()],
        "engines_output": {
            "engine0_packContext": compile_read.compile_result.engine0_output.model_dump(mode="json"),
            "engine1_contextBuilder": compile_read.compile_result.engine1_output.model_dump(mode="json"),
            "engine2_variationController": compile_read.compile_result.engine2_output.model_dump(mode="json"),
            "engine3_patternAssembler": compile_read.compile_result.engine3_output.model_dump(mode="json"),
            "engine4_scriptConverter": compile_read.compile_result.engine4_output.model_dump(mode="json"),
            "engine5_visualDirector": compile_read.compile_result.engine5_output.model_dump(mode="json"),
            "engine6_renderAssembler": compile_read.compile_result.engine6_output.model_dump(mode="json"),
        },
        "render_metadata": {
            "validation_status": compile_read.validator_result.status,
            "validation_checks": [check.model_dump(mode="json") for check in compile_read.validator_result.checks],
        },
    }
