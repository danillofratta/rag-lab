import logging
import re

_BEARER = re.compile(r"(?i)bearer\s+\S+")
_SENSITIVE_ATTRIBUTES = ("authorization", "headers", "body", "token", "session_token")


class SensitiveDataFilter(logging.Filter):
    """Drops authorization headers, tokens, bodies and exception details from records."""

    def filter(self, record: logging.LogRecord) -> bool:
        for name in _SENSITIVE_ATTRIBUTES:
            record.__dict__.pop(name, None)
        record.msg = _BEARER.sub("Bearer [redacted]", record.getMessage())
        record.args = None
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True
