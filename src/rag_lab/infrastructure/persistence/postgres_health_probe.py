from collections.abc import Mapping
from typing import Any

from psycopg_pool import AsyncConnectionPool

from rag_lab.infrastructure.persistence.schema_is_current import schema_is_current


class PostgresHealthProbe:
    def __init__(self, pool: AsyncConnectionPool[Any]) -> None:
        self._pool = pool

    async def check(self) -> Mapping[str, bool]:
        """The database is ready when reachable and migrated; failures carry no details."""
        try:
            async with self._pool.connection(timeout=2) as connection:
                ready = await schema_is_current(connection)
        except Exception:
            ready = False
        return {"database": ready}
