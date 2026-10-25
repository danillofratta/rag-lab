from pathlib import Path
from typing import Any

from psycopg import AsyncConnection

from rag_lab.infrastructure.persistence.discover_migrations import discover_migrations


async def applied_checksums(connection: AsyncConnection[Any]) -> dict[str, str]:
    """Return version to checksum for applied migrations; empty before the first migration."""
    cursor = await connection.execute("select to_regclass('schema_migrations') is not null")
    row = await cursor.fetchone()
    if not (row and row[0]):
        return {}
    cursor = await connection.execute("select version, checksum from schema_migrations")
    return {version: checksum for version, checksum in await cursor.fetchall()}


async def schema_is_current(
    connection: AsyncConnection[Any], directory: Path | None = None
) -> bool:
    """True only when the applied versions are exactly the versions this code expects."""
    expected = {migration.version for migration in discover_migrations(directory)}
    return set(await applied_checksums(connection)) == expected
