from typing import Protocol

from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId


class WorkspaceIdGenerator(Protocol):
    def next_id(self) -> WorkspaceId: ...
