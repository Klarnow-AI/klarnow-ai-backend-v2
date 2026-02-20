"""Central logging for the application. Service actions are logged via the log_service_action decorator."""

import functools
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

# Logger used for all service action events
SERVICE_LOGGER_NAME = "klarnow.services"


def get_logger(name: str = SERVICE_LOGGER_NAME) -> logging.Logger:
    """Return the application logger. Use SERVICE_LOGGER_NAME for service actions."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def _sanitise_arg(value: Any, max_len: int = 200) -> Any:
    """Reduce args for safe logging: skip db, shorten strings, summarise models/collections."""
    if isinstance(value, Session):
        return "<Session>"
    if hasattr(value, "__tablename__"):
        # SQLAlchemy model: log type and id if present
        tid = getattr(value, "id", None)
        return f"<{type(value).__name__}(id={tid})>" if tid else f"<{type(value).__name__}>"
    if isinstance(value, (list, tuple)):
        if len(value) > 5:
            return f"<{type(value).__name__} len={len(value)}>"
        return [_sanitise_arg(v, max_len) for v in value]
    if isinstance(value, dict):
        if len(value) > 10:
            return f"<dict len={len(value)}>"
        return {k: _sanitise_arg(v, max_len) for k, v in list(value.items())[:10]}
    if isinstance(value, str) and len(value) > max_len:
        return value[:max_len] + "..."
    return value


def _sanitise_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in kwargs.items():
        if k == "db":
            continue
        try:
            out[k] = _sanitise_arg(v)
        except Exception:
            out[k] = "<unserialisable>"
    return out


def _log_service_call(log: logging.Logger, module: str, name: str, all_kw: dict[str, Any]) -> None:
    safe = _sanitise_kwargs(all_kw)
    log.info(
        "service_call_start | module=%s | fn=%s | args=%s",
        module,
        name,
        safe,
        extra={"event": "service_call_start", "service_module": module, "service_fn": name, "service_args": safe},
    )


def _log_service_ok(log: logging.Logger, module: str, name: str, duration_ms: float) -> None:
    log.info(
        "service_call_ok | module=%s | fn=%s | duration_ms=%.2f",
        module,
        name,
        duration_ms,
        extra={
            "event": "service_call_ok",
            "service_module": module,
            "service_fn": name,
            "duration_ms": round(duration_ms, 2),
        },
    )


def _log_service_error(log: logging.Logger, module: str, name: str, duration_ms: float, error: str) -> None:
    log.warning(
        "service_call_error | module=%s | fn=%s | duration_ms=%.2f | error=%s",
        module,
        name,
        duration_ms,
        error,
        extra={
            "event": "service_call_error",
            "service_module": module,
            "service_fn": name,
            "duration_ms": round(duration_ms, 2),
            "error": error,
        },
    )


def _build_all_kw(fn: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    all_kw = dict(kwargs)
    try:
        import inspect
        sig = inspect.signature(fn)
        params = list(sig.parameters.keys())
        for i, p in enumerate(params):
            if i < len(args) and p not in all_kw:
                all_kw[p] = args[i]
    except Exception:
        pass
    return all_kw


def log_service_action(logger: logging.Logger | None = None):
    """Decorator that logs every call to a service function: module, name, sanitized args, duration, success/error."""

    def decorator(fn: Any):
        import asyncio

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any):
                log = logger or get_logger()
                module = fn.__module__
                name = fn.__qualname__
                all_kw = _build_all_kw(fn, args, kwargs)
                _log_service_call(log, module, name, all_kw)
                start = time.perf_counter()
                try:
                    result = await fn(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start) * 1000
                    _log_service_ok(log, module, name, duration_ms)
                    return result
                except Exception as e:
                    duration_ms = (time.perf_counter() - start) * 1000
                    _log_service_error(log, module, name, duration_ms, str(e))
                    raise

            return async_wrapper
        else:

            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any):
                log = logger or get_logger()
                module = fn.__module__
                name = fn.__qualname__
                all_kw = _build_all_kw(fn, args, kwargs)
                _log_service_call(log, module, name, all_kw)
                start = time.perf_counter()
                try:
                    result = fn(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start) * 1000
                    _log_service_ok(log, module, name, duration_ms)
                    return result
                except Exception as e:
                    duration_ms = (time.perf_counter() - start) * 1000
                    _log_service_error(log, module, name, duration_ms, str(e))
                    raise

            return wrapper

    return decorator
