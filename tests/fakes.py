"""Deterministic fakes for the technical ports. No I/O, no network."""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Self
from uuid import UUID

from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId
from rag_lab.domain.workspaces.entities.workspace import Workspace

START = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, value: datetime = START) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value

    def advance(self, delta: timedelta) -> None:
        self.value += delta


class SequenceWorkspaceIds:
    def __init__(self) -> None:
        self._counter = 0

    def next_id(self) -> WorkspaceId:
        self._counter += 1
        return WorkspaceId(str(UUID(int=self._counter)))


class SequenceSessionTokens:
    """Tokens shaped like the real ones: 43 URL-safe characters."""

    def __init__(self) -> None:
        self._counter = 0

    def next_token(self) -> str:
        self._counter += 1
        return f"{self._counter:02d}".ljust(43, "A")


class InMemoryWorkspaceRepository:
    def __init__(self, rows: dict[str, Workspace]) -> None:
        self._rows = rows

    async def add(self, workspace: Workspace) -> None:
        self._rows[workspace.id.value] = workspace

    async def find(self, workspace_id: WorkspaceId) -> Workspace | None:
        return self._rows.get(workspace_id.value)

    async def find_by_token_hash(self, token_hash: SessionTokenHash) -> Workspace | None:
        return next((row for row in self._rows.values() if row.token_hash == token_hash), None)


class InMemoryUnitOfWork:
    """Stages writes and publishes them to the shared store only on commit."""

    def __init__(self, store: "InMemoryStore") -> None:
        self._store = store
        self._staged: dict[str, Workspace] = {}
        self.workspaces = InMemoryWorkspaceRepository(self._staged)

    async def __aenter__(self) -> Self:
        self._staged.clear()
        self._staged.update(self._store.rows)
        self._store.entered += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._staged.clear()

    async def commit(self) -> None:
        self._store.rows.clear()
        self._store.rows.update(self._staged)
        self._store.commits += 1

    async def rollback(self) -> None:
        self._staged.clear()


class InMemoryStore:
    """The 'database': committed rows plus counters to prove what was touched."""

    def __init__(self) -> None:
        self.rows: dict[str, Workspace] = {}
        self.entered = 0
        self.commits = 0

    def __call__(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(self)


class FakeHealthProbe:
    def __init__(self, status: Mapping[str, bool]) -> None:
        self.status = dict(status)

    async def check(self) -> Mapping[str, bool]:
        return self.status
