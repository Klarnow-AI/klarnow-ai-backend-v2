"""Database engine and session factory (sync + async)."""

from importlib.util import find_spec
import time
from typing import Any, AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.db.base import Base
from app.core.db.model_registry import load_model_metadata
from app.core.db.observability import record_db_query

load_model_metadata()


def _database_backend_name(database_url: str) -> str:
    return make_url(database_url).get_backend_name()


def _async_database_driver(database_url: str) -> str | None:
    backend = _database_backend_name(database_url)
    if backend == "postgresql" and find_spec("asyncpg") is not None:
        return "postgresql+asyncpg"
    if backend == "sqlite" and find_spec("aiosqlite") is not None:
        return "sqlite+aiosqlite"
    return None


def _async_database_url(database_url: str) -> str | None:
    """Convert a sync database URL to an installed async-driver URL."""
    url = make_url(database_url)
    drivername = _async_database_driver(database_url)
    if drivername is None:
        return None
    return url.set(drivername=drivername).render_as_string(hide_password=False)


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

_async_url = _async_database_url(_settings.database_url)
if _async_url is not None:
    async_engine = create_async_engine(
        _async_url,
        pool_pre_ping=bool(_settings.db_pool_pre_ping),
        pool_size=_settings.db_pool_size,
        max_overflow=_settings.db_max_overflow,
        pool_timeout=_settings.db_pool_timeout_seconds,
        pool_use_lifo=_settings.db_pool_use_lifo,
        **({
            "pool_recycle": _settings.db_pool_recycle_seconds
        } if _settings.db_pool_recycle_seconds > 0 else {}),
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
else:
    async_engine = None
    AsyncSessionLocal = None


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


async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        backend = _database_backend_name(_settings.database_url)
        expected_driver = {
            "postgresql": "asyncpg",
            "sqlite": "aiosqlite",
        }.get(backend, f"a supported async driver for {backend}")
        raise RuntimeError(
            "Async database access is unavailable for the configured database URL. "
            f"Install `{expected_driver}` or use a database URL with a supported async driver."
        )
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
