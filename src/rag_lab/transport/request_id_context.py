from contextvars import ContextVar

NO_REQUEST_ID = "-"
request_id_var: ContextVar[str] = ContextVar("request_id", default=NO_REQUEST_ID)
