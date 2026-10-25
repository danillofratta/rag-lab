from dataclasses import dataclass
from datetime import datetime, timedelta

from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId
from rag_lab.domain.workspaces.exceptions.invalid_workspace import InvalidWorkspace


def _is_aware(moment: datetime) -> bool:
    return moment.tzinfo is not None and moment.utcoffset() is not None


@dataclass(frozen=True)
class Workspace:
    """An anonymous visitor's isolated workspace. It expires and activity never extends it."""

    id: WorkspaceId
    token_hash: SessionTokenHash
    created_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if not (_is_aware(self.created_at) and _is_aware(self.expires_at)):
            raise InvalidWorkspace("Workspace timestamps must be timezone-aware")
        if self.expires_at <= self.created_at:
            raise InvalidWorkspace("Workspace must expire after it is created")

    @classmethod
    def create(
        cls,
        id: WorkspaceId,
        token_hash: SessionTokenHash,
        now: datetime,
        lifetime: timedelta,
    ) -> "Workspace":
        if lifetime <= timedelta(0):
            raise InvalidWorkspace("Workspace lifetime must be positive")
        return cls(id, token_hash, now, now + lifetime)

    def is_expired(self, now: datetime) -> bool:
        """A workspace is expired at its expiry instant, not after it."""
        return now >= self.expires_at
