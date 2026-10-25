from rag_lab.application.exceptions.application_error import ApplicationError


class SessionExpired(ApplicationError):
    """The workspace behind a valid session token has expired."""

    code = "SESSION_EXPIRED"
