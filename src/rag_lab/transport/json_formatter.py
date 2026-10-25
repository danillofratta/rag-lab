import json
import logging
from typing import Any

_EXTRA_FIELDS = ("method", "path", "status", "duration_ms", "exception_type")


class JsonFormatter(logging.Formatter):
    """One JSON object per record; no stack traces."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for name in _EXTRA_FIELDS:
            if hasattr(record, name):
                payload[name] = getattr(record, name)
        return json.dumps(payload)
