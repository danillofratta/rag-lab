from datetime import timedelta

import pytest

from rag_lab.application.exceptions.principal_required import PrincipalRequired
from rag_lab.application.exceptions.session_expired import SessionExpired
from rag_lab.application.exceptions.unauthenticated import Unauthenticated
from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId
from rag_lab.domain.workspaces.entities.workspace import Workspace
from rag_lab.domain.workspaces.value_objects.workspace_principal import WorkspacePrincipal
from rag_lab.features.create_workspace.command import CreateWorkspaceCommand
from rag_lab.features.create_workspace.handler import CreateWorkspaceHandler
from rag_lab.features.get_current_workspace.handler import GetCurrentWorkspaceHandler
from rag_lab.features.get_current_workspace.query import GetCurrentWorkspaceQuery
from tests.fakes import (
    START,
    FakeClock,
    InMemoryStore,
    SequenceSessionTokens,
    SequenceWorkspaceIds,
)

LIFETIME = timedelta(hours=24)


def create_handler(store: InMemoryStore, clock: FakeClock) -> CreateWorkspaceHandler:
    return CreateWorkspaceHandler(
        store, clock, SequenceWorkspaceIds(), SequenceSessionTokens(), LIFETIME
    )


@pytest.mark.anyio
async def test_creation_returns_identifier_token_and_expiry_one_lifetime_later():
    store, clock = InMemoryStore(), FakeClock()
    result = await create_handler(store, clock).handle(CreateWorkspaceCommand())
    assert result.created_at == START
    assert result.expires_at == START + LIFETIME
    assert result.session_token
    assert result.workspace_id.value in store.rows


@pytest.mark.anyio
async def test_creation_stores_only_the_token_hash():
    store, clock = InMemoryStore(), FakeClock()
    result = await create_handler(store, clock).handle(CreateWorkspaceCommand())
    stored = store.rows[result.workspace_id.value]
    assert stored.token_hash == SessionTokenHash.of(result.session_token)
    assert result.session_token not in repr(stored)


@pytest.mark.anyio
async def test_result_repr_does_not_reveal_the_token():
    store, clock = InMemoryStore(), FakeClock()
    result = await create_handler(store, clock).handle(CreateWorkspaceCommand())
    assert result.session_token not in repr(result)


@pytest.mark.anyio
async def test_work_that_is_not_committed_is_discarded():
    store = InMemoryStore()
    uncommitted = Workspace.create(
        WorkspaceId("00000000-0000-4000-8000-0000000000ff"),
        SessionTokenHash.of("other"),
        START,
        LIFETIME,
    )
    async with store() as work:
        await work.workspaces.add(uncommitted)
    assert store.rows == {}


async def seeded(store: InMemoryStore, clock: FakeClock) -> WorkspacePrincipal:
    result = await create_handler(store, clock).handle(CreateWorkspaceCommand())
    return WorkspacePrincipal(result.workspace_id)


@pytest.mark.anyio
async def test_inspection_returns_the_workspace_without_changing_it():
    store, clock = InMemoryStore(), FakeClock()
    principal = await seeded(store, clock)
    before, commits = dict(store.rows), store.commits
    handler = GetCurrentWorkspaceHandler(store, clock)
    first = await handler.handle(GetCurrentWorkspaceQuery(principal))
    clock.advance(timedelta(hours=1))
    second = await handler.handle(GetCurrentWorkspaceQuery(principal))
    assert first == second
    assert first.expires_at == START + LIFETIME
    assert store.rows == before
    assert store.commits == commits


@pytest.mark.anyio
async def test_direct_call_without_a_principal_is_rejected_before_persistence_access():
    store, clock = InMemoryStore(), FakeClock()
    entered = store.entered
    with pytest.raises(PrincipalRequired):
        await GetCurrentWorkspaceHandler(store, clock).handle(GetCurrentWorkspaceQuery(None))
    assert store.entered == entered


@pytest.mark.anyio
async def test_unknown_workspace_is_unauthenticated():
    store, clock = InMemoryStore(), FakeClock()
    ghost = WorkspacePrincipal(WorkspaceId("00000000-0000-4000-8000-0000000000aa"))
    with pytest.raises(Unauthenticated):
        await GetCurrentWorkspaceHandler(store, clock).handle(GetCurrentWorkspaceQuery(ghost))


@pytest.mark.anyio
async def test_expired_workspace_is_rejected_at_the_expiry_instant():
    store, clock = InMemoryStore(), FakeClock()
    principal = await seeded(store, clock)
    handler = GetCurrentWorkspaceHandler(store, clock)
    clock.advance(LIFETIME - timedelta(microseconds=1))
    await handler.handle(GetCurrentWorkspaceQuery(principal))
    clock.advance(timedelta(microseconds=1))
    with pytest.raises(SessionExpired):
        await handler.handle(GetCurrentWorkspaceQuery(principal))
