from typing import Protocol

from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId
from rag_lab.domain.workspaces.entities.workspace import Workspace


class WorkspaceRepository(Protocol):
    async def add(self, workspace: Workspace) -> None: ...

    async def find(self, workspace_id: WorkspaceId) -> Workspace | None: ...

    async def find_by_token_hash(self, token_hash: SessionTokenHash) -> Workspace | None: ...
