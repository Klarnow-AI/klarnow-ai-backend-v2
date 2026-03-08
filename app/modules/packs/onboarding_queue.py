"""Redis Streams queue primitives for onboarding jobs."""

from __future__ import annotations

import json
import socket
import time
import uuid
from functools import lru_cache

from redis import Redis
from redis.exceptions import ResponseError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("klarnow.onboarding_queue")


def redis_queue_enabled() -> bool:
    settings = get_settings()
    return bool(settings.redis_url.strip())


@lru_cache
def get_redis_client() -> Redis:
    settings = get_settings()
    if not settings.redis_url.strip():
        raise RuntimeError("REDIS_URL is not configured")
    return Redis.from_url(settings.redis_url, decode_responses=True)


def build_onboarding_consumer_name() -> str:
    hostname = socket.gethostname().split(".")[0] or "worker"
    return f"{hostname}-{uuid.uuid4().hex[:8]}"


def ensure_onboarding_consumer_group() -> None:
    settings = get_settings()
    client = get_redis_client()
    try:
        client.xgroup_create(
            settings.onboarding_queue_stream_key,
            settings.onboarding_queue_consumer_group,
            id="0-0",
            mkstream=True,
        )
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def _dispatch_key(job_id: str) -> str:
    return f"klarnow:onboarding:dispatch:{job_id}"


def _flatten_messages(
    entries: list[tuple[str, list[tuple[str, dict[str, str]]]]] | None,
) -> list[tuple[str, dict[str, str]]]:
    flattened: list[tuple[str, dict[str, str]]] = []
    for _, messages in entries or []:
        for message_id, payload in messages:
            flattened.append((message_id, payload))
    return flattened


def dispatch_onboarding_job(
    pack_id: str,
    job_id: str,
    *,
    delay_seconds: int = 0,
    force: bool = False,
) -> bool:
    settings = get_settings()
    client = get_redis_client()
    payload = {"pack_id": str(pack_id), "job_id": str(job_id)}
    dispatch_key = _dispatch_key(str(job_id))
    member = json.dumps(payload, sort_keys=True)

    if not force:
        acquired = client.set(
            dispatch_key,
            "1",
            nx=True,
            ex=settings.onboarding_queue_dispatch_ttl_seconds,
        )
        if not acquired:
            return False
    else:
        client.set(
            dispatch_key,
            "1",
            ex=settings.onboarding_queue_dispatch_ttl_seconds,
        )

    try:
        if delay_seconds > 0:
            client.zadd(
                settings.onboarding_queue_delayed_key,
                {member: time.time() + delay_seconds},
            )
        else:
            client.xadd(
                settings.onboarding_queue_stream_key,
                payload,
                maxlen=settings.onboarding_queue_stream_maxlen,
                approximate=True,
            )
        return True
    except Exception:
        if not force:
            client.delete(dispatch_key)
        raise


def clear_onboarding_job_dispatch(job_id: str) -> None:
    client = get_redis_client()
    client.delete(_dispatch_key(str(job_id)))


def promote_due_onboarding_jobs(limit: int | None = None) -> int:
    settings = get_settings()
    client = get_redis_client()
    batch_size = limit or max(1, settings.onboarding_queue_batch_size)
    due_members = client.zrangebyscore(
        settings.onboarding_queue_delayed_key,
        "-inf",
        time.time(),
        start=0,
        num=batch_size,
    )
    promoted = 0
    for member in due_members:
        if not client.zrem(settings.onboarding_queue_delayed_key, member):
            continue
        payload = json.loads(member)
        client.xadd(
            settings.onboarding_queue_stream_key,
            payload,
            maxlen=settings.onboarding_queue_stream_maxlen,
            approximate=True,
        )
        promoted += 1
    return promoted


def read_onboarding_messages(
    consumer_name: str,
    *,
    count: int | None = None,
    block_ms: int | None = None,
) -> list[tuple[str, dict[str, str]]]:
    settings = get_settings()
    client = get_redis_client()
    entries = client.xreadgroup(
        settings.onboarding_queue_consumer_group,
        consumer_name,
        {settings.onboarding_queue_stream_key: ">"},
        count=count or settings.onboarding_queue_batch_size,
        block=block_ms or settings.onboarding_queue_block_ms,
    )
    return _flatten_messages(entries)


def claim_stale_onboarding_messages(
    consumer_name: str,
    *,
    count: int | None = None,
) -> list[tuple[str, dict[str, str]]]:
    settings = get_settings()
    client = get_redis_client()
    batch_size = count or settings.onboarding_queue_batch_size
    pending = client.xpending_range(
        settings.onboarding_queue_stream_key,
        settings.onboarding_queue_consumer_group,
        "-",
        "+",
        batch_size,
    )
    stale_ids = [
        entry["message_id"]
        for entry in pending
        if int(entry.get("time_since_delivered") or 0) >= settings.onboarding_queue_claim_idle_ms
    ]
    if not stale_ids:
        return []
    claimed = client.xclaim(
        settings.onboarding_queue_stream_key,
        settings.onboarding_queue_consumer_group,
        consumer_name,
        settings.onboarding_queue_claim_idle_ms,
        stale_ids,
    )
    return [(message_id, payload) for message_id, payload in claimed]


def ack_onboarding_message(message_id: str) -> None:
    settings = get_settings()
    client = get_redis_client()
    client.xack(
        settings.onboarding_queue_stream_key,
        settings.onboarding_queue_consumer_group,
        message_id,
    )
    client.xdel(settings.onboarding_queue_stream_key, message_id)
