from types import TracebackType
from typing import Any, Self

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from rag_lab.domain.workspaces.repositories.workspace_repository import WorkspaceRepository
from rag_lab.infrastructure.repositories.postgres_workspace_repository import (
    PostgresWorkspaceRepository,
)


class PostgresUnitOfWork:
    """One pooled connection and one transaction; uncommitted work is rolled back on exit."""

    def __init__(self, pool: AsyncConnectionPool[Any]) -> None:
        self._pool = pool
        self._connection: AsyncConnection[Any] | None = None
        self._workspaces: PostgresWorkspaceRepository | None = None

    @property
    def workspaces(self) -> WorkspaceRepository:
        if self._workspaces is None:
            raise RuntimeError("The unit of work is not active")
        return self._workspaces

    async def __aenter__(self) -> Self:
        connection = await self._pool.getconn()
        self._connection = connection
        self._workspaces = PostgresWorkspaceRepository(connection)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        connection = self._connection
        self._connection = None
        self._workspaces = None
        if connection is None:
            return
        try:
            # A no-op after a commit; discards everything else.
            await connection.rollback()
        finally:
            await self._pool.putconn(connection)

    async def commit(self) -> None:
        await self._active().commit()

    async def rollback(self) -> None:
        await self._active().rollback()

    def _active(self) -> AsyncConnection[Any]:
        if self._connection is None:
            raise RuntimeError("The unit of work is not active")
        return self._connection
