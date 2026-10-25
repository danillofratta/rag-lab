from rag_lab.application.exceptions.application_error import ApplicationError


class Unauthenticated(ApplicationError):
    """Missing, malformed or unknown credentials. All three look identical to clients."""

    code = "UNAUTHENTICATED"
