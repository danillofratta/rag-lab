class ApplicationError(Exception):
    """Base of expected failures. The stable ``code`` is the only detail exposed to clients."""

    code = "INTERNAL_ERROR"

    def __init__(self) -> None:
        super().__init__(self.code)
