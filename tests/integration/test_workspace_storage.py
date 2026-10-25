from datetime import timedelta

import pytest

from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.features.create_workspace.command import CreateWorkspaceCommand
from rag_lab.features.create_workspace.handler import CreateWorkspaceHandler
from rag_lab.infrastructure.persistence.migrate import apply_migrations
from rag_lab.infrastructure.persistence.postgres_unit_of_work_factory import (
    PostgresUnitOfWorkFactory,
)
from rag_lab.infrastructure.runtime.secrets_session_token_generator import (
    SecretsSessionTokenGenerator,
)
from rag_lab.infrastructure.runtime.uuid_workspace_id_generator import UuidWorkspaceIdGenerator
from tests.fakes import FakeClock

pytestmark = pytest.mark.anyio

LIFETIME = timedelta(hours=24)


def real_handler(factory):
    return CreateWorkspaceHandler(
        factory,
        FakeClock(),
        UuidWorkspaceIdGenerator(),
        SecretsSessionTokenGenerator(),
        LIFETIME,
    )


async def test_only_the_token_hash_is_stored(pool, connection):
    await apply_migrations(connection)
    result = await real_handler(PostgresUnitOfWorkFactory(pool)).handle(CreateWorkspaceCommand())

    cursor = await connection.execute(
        "select id::text, token_hash, created_at, expires_at from workspaces"
    )
    [row] = await cursor.fetchall()
    assert row[0] == result.workspace_id.value
    assert row[1] == SessionTokenHash.of(result.session_token).value
    assert result.session_token not in " ".join(str(value) for value in row)
    assert row[3] - row[2] == LIFETIME

    cursor = await connection.execute(
        "select * from workspaces where token_hash = %s", (result.session_token,)
    )
    assert await cursor.fetchall() == []


async def test_workspace_round_trips_through_the_repository(pool, connection):
    await apply_migrations(connection)
    factory = PostgresUnitOfWorkFactory(pool)
    result = await real_handler(factory).handle(CreateWorkspaceCommand())
    token_hash = SessionTokenHash.of(result.session_token)
    async with factory() as work:
        by_id = await work.workspaces.find(result.workspace_id)
        by_hash = await work.workspaces.find_by_token_hash(token_hash)
    assert by_id is not None
    assert by_id == by_hash
    assert by_id.expires_at == result.expires_at
