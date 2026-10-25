import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from rag_lab.transport.error_envelope import error_response
from rag_lab.transport.request_id_context import request_id_var
from rag_lab.transport.request_id_filter import RequestIdFilter
from rag_lab.transport.sensitive_data_filter import SensitiveDataFilter

HEADER = "x-request-id"
_WELL_FORMED = re.compile(r"[A-Za-z0-9-]{8,64}")

logger = logging.getLogger("rag_lab.access")
logger.addFilter(RequestIdFilter())
logger.addFilter(SensitiveDataFilter())


class RequestContextMiddleware:
    """Identifies every request, writes the access log and turns crashes into a 500 envelope.

    Only the method, path, status and duration are logged: never headers, query or bodies.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = self._request_id(scope)
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status = 500
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                MutableHeaders(scope=message)[HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception as error:
            # Only the exception type is logged: its text may carry user data.
            logger.error("unhandled exception", extra={"exception_type": type(error).__name__})
            status = 500
            if not response_started:
                await error_response("INTERNAL_ERROR")(scope, receive, send_with_id)
        finally:
            logger.info(
                "request handled",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            request_id_var.reset(token)

    @staticmethod
    def _request_id(scope: Scope) -> str:
        for name, value in scope["headers"]:
            if name == HEADER.encode():
                candidate: str = value.decode("latin-1")
                if _WELL_FORMED.fullmatch(candidate):
                    return candidate
        return uuid4().hex
