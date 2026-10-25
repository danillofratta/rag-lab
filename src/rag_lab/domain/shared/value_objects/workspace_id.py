from dataclasses import dataclass
from uuid import UUID

from rag_lab.domain.shared.exceptions.invalid_workspace_id import InvalidWorkspaceId


@dataclass(frozen=True)
class WorkspaceId:
    """Identifier of an anonymous workspace: a canonical lowercase UUID."""

    value: str

    def __post_init__(self) -> None:
        try:
            canonical = str(UUID(self.value))
        except (ValueError, AttributeError, TypeError):
            raise InvalidWorkspaceId("Workspace identifier is not a UUID") from None
        if canonical != self.value:
            raise InvalidWorkspaceId("Workspace identifier is not in canonical form")

    def __str__(self) -> str:
        return self.value
