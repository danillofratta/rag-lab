from typing import Protocol


class SessionTokenGenerator(Protocol):
    def next_token(self) -> str:
        """Return a new unguessable session token with at least 256 bits of randomness."""
        ...
