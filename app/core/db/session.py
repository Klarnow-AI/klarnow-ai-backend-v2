"""Database engine and session factory."""

import time
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.db.base import Base
from app.core.db.model_registry import load_model_metadata
from app.core.db.observability import record_db_query

load_model_metadata()


def _database_backend_name(database_url: str) -> str:
    return make_url(database_url).get_backend_name()


def _build_engine_kwargs(settings) -> dict[str, Any]:
    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": bool(settings.db_pool_pre_ping),
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout_seconds,
        "pool_use_lifo": settings.db_pool_use_lifo,
    }
    if settings.db_pool_recycle_seconds > 0:
        engine_kwargs["pool_recycle"] = settings.db_pool_recycle_seconds
    if settings.db_connect_timeout_seconds > 0:
        timeout_key = (
            "timeout"
            if _database_backend_name(settings.database_url) == "sqlite"
            else "connect_timeout"
        )
        engine_kwargs["connect_args"] = {
            timeout_key: settings.db_connect_timeout_seconds,
        }
    return engine_kwargs


_settings = get_settings()
engine_kwargs = _build_engine_kwargs(_settings)

engine = create_engine(
    _settings.database_url,
    **engine_kwargs,
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)


@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    starts = conn.info.setdefault("_query_start_time", [])
    starts.append(time.perf_counter())


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    starts = conn.info.get("_query_start_time") or []
    started_at = starts.pop() if starts else None
    if started_at is None:
        return
    record_db_query((time.perf_counter() - started_at) * 1000)


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        db.close()
