from __future__ import annotations

import json
import logging
import logging.config
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .configuration import Settings

try:
    from opentelemetry import trace as _otel_trace
except ImportError:  # pragma: no cover
    _otel_trace = None  # type: ignore[assignment]

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

_STANDARD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "taskName",
    "color_message",
}
_CONTEXT_ATTRS = ("request_id", "trace_id", "span_id")


def _current_trace_ids() -> tuple[str | None, str | None]:
    if _otel_trace is None:
        return None, None
    ctx = _otel_trace.get_current_span().get_span_context()
    if not ctx.is_valid:
        return None, None
    return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", None) or request_id_ctx.get() or "-"
        trace_id, span_id = _current_trace_ids()
        record.trace_id = getattr(record, "trace_id", None) or trace_id
        record.span_id = getattr(record, "span_id", None) or span_id
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _CONTEXT_ATTRS:
            value = getattr(record, key, None)
            if value not in (None, "-"):
                payload[key] = value
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in _CONTEXT_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(settings: Settings) -> None:
    level = settings.log.level.upper()
    formatter = settings.log_format.value
    quiet = {"level": "WARNING", "handlers": [], "propagate": True}

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"context": {"()": ContextFilter}},
            "formatters": {
                "json": {"()": JsonFormatter},
                "text": {
                    "format": "%(asctime)s %(levelname)-8s %(name)s [%(request_id)s] %(message)s",
                    "datefmt": "%H:%M:%S",
                },
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": formatter,
                    "filters": ["context"],
                }
            },
            "root": {"level": level, "handlers": ["stdout"]},
            "loggers": {
                "uvicorn": {"level": level, "handlers": [], "propagate": True},
                "uvicorn.error": {"level": level, "handlers": [], "propagate": True},
                "uvicorn.access": {"level": "WARNING", "handlers": [], "propagate": False},
                "sqlalchemy.engine": {
                    "level": "INFO" if settings.database.echo else "WARNING",
                    "handlers": [],
                    "propagate": True,
                },
                "httpx": quiet,
                "httpcore": quiet,
                "asyncio": quiet,
            },
        }
    )
    logging.captureWarnings(True)
