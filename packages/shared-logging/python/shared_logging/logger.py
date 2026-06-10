"""JSON-structured logging using loguru."""
import sys
import json
from contextvars import ContextVar
from loguru import logger

# Per-request correlation id (set by API gateway, propagated downstream)
correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def _json_sink(message):
    record = message.record
    extra = dict(record["extra"])
    out = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "service": extra.pop("service", "unknown"),
        "correlation_id": extra.pop("correlation_id", correlation_id.get()),
        "event": extra.pop("event", None),
        "message": record["message"],
    }
    if extra:
        out["extra"] = extra
    print(json.dumps(out), file=sys.stdout, flush=True)


def setup(service: str):
    """Configure the global logger for a service."""
    logger.remove()
    logger.add(_json_sink, level="DEBUG")
    return logger.bind(service=service)


def get_logger():
    return logger
