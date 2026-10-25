"""Apply pending schema migrations: ``python -m rag_lab.infrastructure.persistence.migrate``."""

import asyncio
from pathlib import Path
from typing import Any

from psycopg import AsyncConnection

from rag_lab.infrastructure.persistence.discover_migrations import discover_migrations
from rag_lab.infrastructure.persistence.migration_error import MigrationError
from rag_lab.infrastructure.persistence.schema_is_current import applied_checksums
from rag_lab.infrastructure.settings.load_settings import load_settings

# Serializes concurrent runs against the same database.
_LOCK_KEY = 7_204_001


async def apply_migrations(
    connection: AsyncConnection[Any], directory: Path | None = None
) -> list[str]:
    """Apply pending migrations in order, once each, and return their names.

    The connection must be in autocommit mode: each migration runs in its own transaction.
    A migration that was already applied but changed on disk is refused by name.
    """
    migrations = discover_migrations(directory)
    await connection.execute("select pg_advisory_lock(%s)", (_LOCK_KEY,))
    try:
        applied = await applied_checksums(connection)
        known = {migration.version: migration for migration in migrations}
        for version, checksum in applied.items():
            if version not in known:
                raise MigrationError(f"Applied migration is missing from the code: {version}")
            if known[version].checksum != checksum:
                raise MigrationError(f"Applied migration was changed: {version}")
        pending = [migration for migration in migrations if migration.version not in applied]
        if applied and pending and pending[0].version < max(applied):
            raise MigrationError(f"Migration would be applied out of order: {pending[0].version}")
        for migration in pending:
            async with connection.transaction():
                await connection.execute(migration.sql)
                await connection.execute(
                    "insert into schema_migrations (version, checksum) values (%s, %s)",
                    (migration.version, migration.checksum),
                )
        return [migration.version for migration in pending]
    finally:
        await connection.execute("select pg_advisory_unlock(%s)", (_LOCK_KEY,))


async def run() -> None:
    settings = load_settings()
    url = settings.database_url.get_secret_value()
    async with await AsyncConnection.connect(url, autocommit=True) as connection:
        applied = await apply_migrations(connection)
    print("Applied migrations:", ", ".join(applied) if applied else "none")


def main() -> None:
    # psycopg needs a selector event loop, which is not the default on Windows.
    asyncio.run(run(), loop_factory=asyncio.SelectorEventLoop)


if __name__ == "__main__":
    main()
