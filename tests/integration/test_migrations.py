import shutil
from datetime import timedelta

import pytest
from psycopg.errors import DivisionByZero

from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId
from rag_lab.domain.workspaces.entities.workspace import Workspace
from rag_lab.infrastructure.persistence.create_pool import create_pool
from rag_lab.infrastructure.persistence.discover_migrations import (
    MIGRATIONS_DIRECTORY,
    discover_migrations,
)
from rag_lab.infrastructure.persistence.migrate import apply_migrations
from rag_lab.infrastructure.persistence.migration_error import MigrationError
from rag_lab.infrastructure.persistence.postgres_health_probe import PostgresHealthProbe
from rag_lab.infrastructure.persistence.postgres_unit_of_work_factory import (
    PostgresUnitOfWorkFactory,
)
from rag_lab.infrastructure.persistence.schema_is_current import schema_is_current
from tests.fakes import START

pytestmark = pytest.mark.anyio


async def recorded(connection):
    cursor = await connection.execute("select version from schema_migrations order by version")
    return [row[0] for row in await cursor.fetchall()]


async def test_migrations_apply_in_order_exactly_once(connection):
    expected = [migration.version for migration in discover_migrations()]
    assert await apply_migrations(connection) == expected
    assert await recorded(connection) == expected


async def test_a_second_run_applies_nothing_and_succeeds(connection):
    await apply_migrations(connection)
    assert await apply_migrations(connection) == []


async def test_a_changed_applied_migration_is_refused_by_name(connection, tmp_path):
    for source in MIGRATIONS_DIRECTORY.glob("*.sql"):
        shutil.copy(source, tmp_path / source.name)
    await apply_migrations(connection, tmp_path)
    first = sorted(tmp_path.glob("*.sql"))[0]
    first.write_text(first.read_text(encoding="utf-8") + "\n-- tampered\n", encoding="utf-8")
    with pytest.raises(MigrationError, match=first.stem):
        await apply_migrations(connection, tmp_path)


async def test_an_applied_migration_missing_from_the_code_is_refused(connection, tmp_path):
    for source in MIGRATIONS_DIRECTORY.glob("*.sql"):
        shutil.copy(source, tmp_path / source.name)
    await apply_migrations(connection, tmp_path)
    removed = sorted(tmp_path.glob("*.sql"))[-1]
    removed.unlink()
    with pytest.raises(MigrationError, match=removed.stem):
        await apply_migrations(connection, tmp_path)


async def test_a_failing_migration_leaves_no_partial_effect(connection, tmp_path):
    (tmp_path / "0001_ledger.sql").write_text(
        (MIGRATIONS_DIRECTORY / "0001_schema_migrations.sql").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "0002_broken.sql").write_text(
        "create table half_done (id int);\nselect 1/0;", encoding="utf-8"
    )
    with pytest.raises(DivisionByZero):
        await apply_migrations(connection, tmp_path)
    cursor = await connection.execute("select to_regclass('half_done') is null")
    assert (await cursor.fetchone())[0] is True
    assert await recorded(connection) == ["0001_ledger"]


async def test_schema_is_current_only_when_fully_migrated(connection):
    assert not await schema_is_current(connection)
    await apply_migrations(connection)
    assert await schema_is_current(connection)


async def test_readiness_probe_reports_pending_migrations_as_not_ready(pool, connection):
    probe = PostgresHealthProbe(pool)
    assert await probe.check() == {"database": False}
    await apply_migrations(connection)
    assert await probe.check() == {"database": True}


async def test_readiness_probe_reports_an_unreachable_database_as_not_ready():
    pool = create_pool("postgresql://nobody:nothing@127.0.0.1:1/none")
    await pool.open()
    try:
        assert await PostgresHealthProbe(pool).check() == {"database": False}
    finally:
        await pool.close()


async def test_a_rolled_back_unit_of_work_leaves_no_rows(pool, connection):
    await apply_migrations(connection)
    workspace = Workspace.create(
        WorkspaceId("00000000-0000-4000-8000-000000000001"),
        SessionTokenHash.of("token"),
        START,
        timedelta(hours=1),
    )
    factory = PostgresUnitOfWorkFactory(pool)
    async with factory() as work:
        await work.workspaces.add(workspace)
        await work.rollback()
    async with factory() as work:
        await work.workspaces.add(workspace)  # never committed
    async with factory() as work:
        assert await work.workspaces.find(workspace.id) is None
    cursor = await connection.execute("select count(*) from workspaces")
    assert (await cursor.fetchone())[0] == 0


async def test_an_exception_inside_the_unit_of_work_discards_its_writes(pool, connection):
    await apply_migrations(connection)
    workspace = Workspace.create(
        WorkspaceId("00000000-0000-4000-8000-000000000002"),
        SessionTokenHash.of("token"),
        START,
        timedelta(hours=1),
    )
    with pytest.raises(RuntimeError):
        async with PostgresUnitOfWorkFactory(pool)() as work:
            await work.workspaces.add(workspace)
            raise RuntimeError("boom")
    cursor = await connection.execute("select count(*) from workspaces")
    assert (await cursor.fetchone())[0] == 0
