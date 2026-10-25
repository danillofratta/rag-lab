import logging

from rag_lab.transport.json_formatter import JsonFormatter
from rag_lab.transport.request_id_filter import RequestIdFilter
from rag_lab.transport.sensitive_data_filter import SensitiveDataFilter

HANDLER_NAME = "rag_lab_json"


def configure_logging(level: str) -> None:
    """Install the structured, sanitizing handler once and set the package log level."""
    root = logging.getLogger()
    if not any(handler.get_name() == HANDLER_NAME for handler in root.handlers):
        handler = logging.StreamHandler()
        handler.set_name(HANDLER_NAME)
        handler.setFormatter(JsonFormatter())
        handler.addFilter(RequestIdFilter())
        handler.addFilter(SensitiveDataFilter())
        root.addHandler(handler)
    logging.getLogger("rag_lab").setLevel(level)
