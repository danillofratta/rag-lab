from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI

from rag_lab.components import Components
from rag_lab.features.check_health.handler import CheckHealthHandler
from rag_lab.features.create_workspace.handler import CreateWorkspaceHandler
from rag_lab.features.get_current_workspace.handler import GetCurrentWorkspaceHandler
from rag_lab.infrastructure.settings.settings import Settings
from rag_lab.main import create_app
from tests.fakes import (
    FakeClock,
    FakeHealthProbe,
    InMemoryStore,
    SequenceSessionTokens,
    SequenceWorkspaceIds,
)

LIFETIME_HOURS = 24
BODY_LIMIT = 64


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql://rag_lab:unit-test-secret@127.0.0.1:5432/rag_lab",
        "workspace_lifetime_hours": LIFETIME_HOURS,
        "max_body_bytes": BODY_LIMIT,
        "docs_enabled": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


class Harness:
    """A fully faked application plus the fakes tests inspect and steer."""

    def __init__(self, **settings_overrides: object) -> None:
        self.settings = make_settings(**settings_overrides)
        self.store = InMemoryStore()
        self.clock = FakeClock()
        self.probe = FakeHealthProbe({"database": True})
        self.components = Components(
            settings=self.settings,
            clock=self.clock,
            unit_of_work=self.store,
            create_workspace=CreateWorkspaceHandler(
                self.store,
                self.clock,
                SequenceWorkspaceIds(),
                SequenceSessionTokens(),
                timedelta(hours=self.settings.workspace_lifetime_hours),
            ),
            get_current_workspace=GetCurrentWorkspaceHandler(self.store, self.clock),
            check_health=CheckHealthHandler(self.probe),
        )
        self.app: FastAPI = create_app(self.settings, self._opener())

    def _opener(self) -> Callable[[], AbstractAsyncContextManager[Components]]:
        @asynccontextmanager
        async def open_components() -> AsyncIterator[Components]:
            yield self.components

        return open_components

    @asynccontextmanager
    async def client(self) -> AsyncIterator[httpx.AsyncClient]:
        async with self.app.router.lifespan_context(self.app):
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                yield client


@pytest.fixture
def harness() -> Harness:
    return Harness()


@pytest.fixture
def docs_harness() -> Harness:
    return Harness(docs_enabled=True)


@pytest.fixture
async def client(harness: Harness) -> AsyncIterator[httpx.AsyncClient]:
    async with harness.client() as active:
        yield active
