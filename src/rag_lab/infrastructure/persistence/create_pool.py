from typing import Any

from psycopg_pool import AsyncConnectionPool


def create_pool(database_url: str) -> AsyncConnectionPool[Any]:
    """Build the connection pool closed; the API lifespan opens and closes it."""
    return AsyncConnectionPool(database_url, min_size=1, max_size=10, timeout=5, open=False)
