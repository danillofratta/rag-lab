import logging

from rag_lab.transport.request_id_context import request_id_var


class RequestIdFilter(logging.Filter):
    """Stamps every record with the identifier of the request being handled."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True
