"""Database engine and session factory."""

import time

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.db.base import Base
from app.core.db.model_registry import load_model_metadata
from app.core.db.observability import record_db_query

load_model_metadata()

_settings = get_settings()
engine_kwargs = {
    "pool_pre_ping": bool(_settings.db_pool_pre_ping),
    "pool_size": _settings.db_pool_size,
    "max_overflow": _settings.db_max_overflow,
    "pool_timeout": _settings.db_pool_timeout_seconds,
    "pool_use_lifo": _settings.db_pool_use_lifo,
}
if _settings.db_pool_recycle_seconds > 0:
    engine_kwargs["pool_recycle"] = _settings.db_pool_recycle_seconds
if _settings.db_connect_timeout_seconds > 0:
    engine_kwargs["connect_args"] = {
        "connect_timeout": _settings.db_connect_timeout_seconds,
    }

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
