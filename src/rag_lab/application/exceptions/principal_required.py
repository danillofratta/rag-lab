from rag_lab.application.exceptions.application_error import ApplicationError


class PrincipalRequired(ApplicationError):
    """A workspace-scoped use case was invoked without a trusted workspace principal."""

    code = "UNAUTHENTICATED"
