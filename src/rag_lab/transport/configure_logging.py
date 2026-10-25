import logging

HANDLER_NAME = "rag_lab_json"


def configure_logging(handler: logging.Handler, level: str) -> None:
    """Install the structured, sanitizing handler once and set the package log level.

    The composition root builds the handler; this only registers it.
    """
    handler.set_name(HANDLER_NAME)
    root = logging.getLogger()
    if not any(existing.get_name() == HANDLER_NAME for existing in root.handlers):
        root.addHandler(handler)
    logging.getLogger("rag_lab").setLevel(level)
