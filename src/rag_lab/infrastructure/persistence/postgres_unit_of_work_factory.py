from typing import Any

from psycopg_pool import AsyncConnectionPool

from rag_lab.infrastructure.persistence.postgres_unit_of_work import PostgresUnitOfWork


class PostgresUnitOfWorkFactory:
    def __init__(self, pool: AsyncConnectionPool[Any]) -> None:
        self._pool = pool

    def __call__(self) -> PostgresUnitOfWork:
        return PostgresUnitOfWork(self._pool)
