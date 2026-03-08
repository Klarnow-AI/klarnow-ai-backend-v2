"""Dedicated Redis-backed onboarding worker."""

from __future__ import annotations

import time
from uuid import UUID

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.packs.onboarding_jobs import run_onboarding_job
from app.modules.packs.onboarding_queue import (
    ack_onboarding_message,
    build_onboarding_consumer_name,
    claim_stale_onboarding_messages,
    clear_onboarding_job_dispatch,
    dispatch_onboarding_job,
    ensure_onboarding_consumer_group,
    promote_due_onboarding_jobs,
    read_onboarding_messages,
    redis_queue_enabled,
)

logger = get_logger("klarnow.onboarding_worker")


def _retry_delay_seconds(attempt: int) -> int:
    settings = get_settings()
    base_delay = max(1, settings.onboarding_queue_retry_base_delay_seconds)
    max_delay = max(base_delay, settings.onboarding_queue_retry_max_delay_seconds)
    return min(max_delay, max(base_delay, 2 ** attempt))


def _process_message(message_id: str, payload: dict[str, str]) -> None:
    pack_id = str(payload.get("pack_id") or "").strip()
    job_id = str(payload.get("job_id") or "").strip()
    if not pack_id or not job_id:
        ack_onboarding_message(message_id)
        if job_id:
            clear_onboarding_job_dispatch(job_id)
        logger.warning("Dropped malformed onboarding message id=%s payload=%s", message_id, payload)
        return

    try:
        pack_uuid = UUID(pack_id)
    except ValueError:
        ack_onboarding_message(message_id)
        clear_onboarding_job_dispatch(job_id)
        logger.warning("Dropped onboarding message with invalid pack id=%s job_id=%s", pack_id, job_id)
        return

    result = run_onboarding_job(pack_uuid, job_id)
    if result.retry:
        delay_seconds = _retry_delay_seconds(result.attempt)
        dispatch_onboarding_job(
            str(pack_uuid),
            job_id,
            delay_seconds=delay_seconds,
            force=True,
        )
        ack_onboarding_message(message_id)
        logger.info(
            "Requeued onboarding job pack_id=%s job_id=%s attempt=%s delay_seconds=%s",
            pack_id,
            job_id,
            result.attempt,
            delay_seconds,
        )
        return

    ack_onboarding_message(message_id)
    if result.clear_dispatch:
        clear_onboarding_job_dispatch(job_id)
    logger.info(
        "Finished onboarding job pack_id=%s job_id=%s retry=%s attempt=%s",
        pack_id,
        job_id,
        result.retry,
        result.attempt,
    )


def run_forever() -> None:
    if not redis_queue_enabled():
        raise SystemExit("REDIS_URL is not configured")

    consumer_name = build_onboarding_consumer_name()
    ensure_onboarding_consumer_group()
    logger.info("Onboarding worker started consumer=%s", consumer_name)

    while True:
        try:
            promote_due_onboarding_jobs()
            messages = claim_stale_onboarding_messages(consumer_name)
            if not messages:
                messages = read_onboarding_messages(consumer_name)
            if not messages:
                continue
            for message_id, payload in messages:
                _process_message(message_id, payload)
        except KeyboardInterrupt:
            logger.info("Onboarding worker shutting down")
            return
        except RedisError as exc:
            logger.warning("Redis error in onboarding worker: %s", exc)
            time.sleep(2)
        except Exception:
            logger.exception("Unhandled onboarding worker error")
            time.sleep(2)


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()
