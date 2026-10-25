import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from psycopg import AsyncConnection

from rag_lab.infrastructure.persistence.create_pool import create_pool


def pytest_collection_modifyitems(items):
    for item in items:
        if "tests/integration" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.integration)


@pytest.fixture
async def schema_url() -> AsyncIterator[str]:
    """A database URL whose search_path is a fresh schema, dropped afterwards."""
    base = os.environ["RAG_LAB_DATABASE_URL"]
    schema = "t_" + uuid4().hex[:12]
    async with await AsyncConnection.connect(base, autocommit=True) as admin:
        await admin.execute(f'create schema "{schema}"')
    separator = "&" if "?" in base else "?"
    try:
        yield f"{base}{separator}options=-csearch_path%3D{schema}"
    finally:
        async with await AsyncConnection.connect(base, autocommit=True) as admin:
            await admin.execute(f'drop schema "{schema}" cascade')


@pytest.fixture
async def connection(schema_url: str) -> AsyncIterator[AsyncConnection]:
    async with await AsyncConnection.connect(schema_url, autocommit=True) as active:
        yield active


@pytest.fixture
async def pool(schema_url: str):
    opened = create_pool(schema_url)
    await opened.open(wait=True)
    try:
        yield opened
    finally:
        await opened.close()
