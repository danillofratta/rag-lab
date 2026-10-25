from typing import Any
from uuid import UUID

from psycopg import AsyncConnection

from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId
from rag_lab.domain.workspaces.entities.workspace import Workspace

_COLUMNS = "id, token_hash, created_at, expires_at"


class PostgresWorkspaceRepository:
    def __init__(self, connection: AsyncConnection[Any]) -> None:
        self._connection = connection

    async def add(self, workspace: Workspace) -> None:
        await self._connection.execute(
            "insert into workspaces (id, token_hash, created_at, expires_at) "
            "values (%s, %s, %s, %s)",
            (
                UUID(workspace.id.value),
                workspace.token_hash.value,
                workspace.created_at,
                workspace.expires_at,
            ),
        )

    async def find(self, workspace_id: WorkspaceId) -> Workspace | None:
        cursor = await self._connection.execute(
            f"select {_COLUMNS} from workspaces where id = %s", (UUID(workspace_id.value),)
        )
        return self._workspace(await cursor.fetchone())

    async def find_by_token_hash(self, token_hash: SessionTokenHash) -> Workspace | None:
        cursor = await self._connection.execute(
            f"select {_COLUMNS} from workspaces where token_hash = %s", (token_hash.value,)
        )
        return self._workspace(await cursor.fetchone())

    @staticmethod
    def _workspace(row: tuple[Any, ...] | None) -> Workspace | None:
        if row is None:
            return None
        return Workspace(WorkspaceId(str(row[0])), SessionTokenHash(row[1]), row[2], row[3])
