from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from rag_lab.application.exceptions.application_error import ApplicationError
from rag_lab.transport.error_envelope import CODE_BY_STATUS, error_response


def register_error_handlers(app: FastAPI) -> None:
    async def application_error(request: Request, error: Exception) -> JSONResponse:
        code = error.code if isinstance(error, ApplicationError) else "INTERNAL_ERROR"
        return error_response(code)

    async def invalid_input(request: Request, error: Exception) -> JSONResponse:
        # Validation errors carry the rejected input; none of it is returned.
        return error_response("INVALID_INPUT")

    async def http_error(request: Request, error: Exception) -> JSONResponse:
        status = error.status_code if isinstance(error, StarletteHTTPException) else 500
        code = CODE_BY_STATUS.get(status, "INTERNAL_ERROR" if status >= 500 else "INVALID_INPUT")
        return error_response(code, status)

    app.add_exception_handler(ApplicationError, application_error)
    app.add_exception_handler(RequestValidationError, invalid_input)
    app.add_exception_handler(StarletteHTTPException, http_error)
