import hashlib
import re
from dataclasses import dataclass

from rag_lab.domain.shared.exceptions.invalid_session_token_hash import InvalidSessionTokenHash

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class SessionTokenHash:
    """One-way SHA-256 digest of a session token. The token itself is never stored."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _SHA256_HEX.fullmatch(self.value):
            raise InvalidSessionTokenHash("Session token hash is not a SHA-256 hex digest")

    @classmethod
    def of(cls, token: str) -> "SessionTokenHash":
        if not token:
            raise InvalidSessionTokenHash("Session token is empty")
        return cls(hashlib.sha256(token.encode("utf-8")).hexdigest())

    def __repr__(self) -> str:
        return "SessionTokenHash(...)"
