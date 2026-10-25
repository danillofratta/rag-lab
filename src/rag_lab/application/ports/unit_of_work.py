from types import TracebackType
from typing import Protocol, Self

from rag_lab.domain.workspaces.repositories.workspace_repository import WorkspaceRepository


class UnitOfWork(Protocol):
    """One transaction. Nothing is persisted unless ``commit`` is awaited before exit."""

    @property
    def workspaces(self) -> WorkspaceRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
