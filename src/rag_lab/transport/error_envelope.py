from fastapi.responses import JSONResponse

STATUS_BY_CODE = {
    "UNAUTHENTICATED": 401,
    "SESSION_EXPIRED": 401,
    "NOT_FOUND": 404,
    "METHOD_NOT_ALLOWED": 405,
    "BODY_TOO_LARGE": 413,
    "INVALID_INPUT": 422,
    "INTERNAL_ERROR": 500,
}
CODE_BY_STATUS = {
    401: "UNAUTHENTICATED",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "BODY_TOO_LARGE",
    422: "INVALID_INPUT",
}


def error_response(code: str, status: int | None = None) -> JSONResponse:
    """The only error shape clients see: a stable code, never a message, input or trace."""
    if code not in STATUS_BY_CODE:
        code = "INTERNAL_ERROR"
    return JSONResponse({"error": code}, status_code=status or STATUS_BY_CODE[code])
