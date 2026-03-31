"""Brand OS helpers shared by onboarding stages."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.packs.models import Pack

from .common import _summary_text_or_none
from .constants import BRAND_OS_INPUT_FINGERPRINT_KEY
from .state import _get_cached_fingerprint


def _get_existing_onboarding_brand_os(
    db: Session,
    pack: Pack,
    job_id: str,
    *,
    expected_input_fingerprint: str | None = None,
):
    from app.modules.brand_os.services import get_by_id_and_pack, get_by_source_job_id

    existing = get_by_source_job_id(db, pack.id, job_id)
    if existing:
        return existing

    answers = pack.onboarding_answers or {}
    if expected_input_fingerprint and (
        _get_cached_fingerprint(pack, BRAND_OS_INPUT_FINGERPRINT_KEY)
        != expected_input_fingerprint
    ):
        return None
    brand_os_id = answers.get("onboarding_brand_os_id")
    if not brand_os_id:
        return None
    try:
        return get_by_id_and_pack(db, UUID(str(brand_os_id)), pack.id)
    except (TypeError, ValueError):
        return None


def _sync_pack_core_concept(pack: Pack, brand_os) -> None:
    from app.modules.brand_os.services import get_summary_fields

    mission, _, _ = get_summary_fields(brand_os)
    mission_text = _summary_text_or_none(mission)
    if mission_text:
        pack.core_concept = mission_text[:500]

