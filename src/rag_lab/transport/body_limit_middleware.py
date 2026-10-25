from fastapi import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from rag_lab.transport.error_envelope import error_response


class BodyLimitMiddleware:
    """Rejects bodies over the limit with 413, declared by length or streamed in chunks."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        for name, value in scope["headers"]:
            if name == b"content-length" and value.isdigit() and int(value) > self.max_bytes:
                # Refused before the application, and so the handler, ever runs.
                await error_response("BODY_TOO_LARGE")(scope, receive, send)
                return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    # FastAPI's own HTTPException is re-raised by body parsing, not rewrapped.
                    raise HTTPException(status_code=413)
            return message

        await self.app(scope, limited_receive, send)
