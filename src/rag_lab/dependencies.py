"""The composition root: the only place concrete adapters are constructed and wired."""

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg_pool import AsyncConnectionPool

from rag_lab.application.exceptions.session_expired import SessionExpired
from rag_lab.application.exceptions.unauthenticated import Unauthenticated
from rag_lab.components import Components
from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.domain.workspaces.value_objects.workspace_principal import WorkspacePrincipal
from rag_lab.features.check_health.handler import CheckHealthHandler
from rag_lab.features.create_workspace.handler import CreateWorkspaceHandler
from rag_lab.features.get_current_workspace.handler import GetCurrentWorkspaceHandler
from rag_lab.infrastructure.persistence.create_pool import create_pool
from rag_lab.infrastructure.persistence.postgres_health_probe import PostgresHealthProbe
from rag_lab.infrastructure.persistence.postgres_unit_of_work_factory import (
    PostgresUnitOfWorkFactory,
)
from rag_lab.infrastructure.runtime.secrets_session_token_generator import (
    SecretsSessionTokenGenerator,
)
from rag_lab.infrastructure.runtime.system_clock import SystemClock
from rag_lab.infrastructure.runtime.uuid_workspace_id_generator import UuidWorkspaceIdGenerator
from rag_lab.infrastructure.settings.settings import Settings

# 32 random bytes encode to 43 URL-safe characters; anything else cannot be a session token.
_SESSION_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")
_bearer = HTTPBearer(auto_error=False)


def build_components(settings: Settings, pool: AsyncConnectionPool[Any]) -> Components:
    clock = SystemClock()
    unit_of_work = PostgresUnitOfWorkFactory(pool)
    return Components(
        settings=settings,
        clock=clock,
        unit_of_work=unit_of_work,
        create_workspace=CreateWorkspaceHandler(
            unit_of_work,
            clock,
            UuidWorkspaceIdGenerator(),
            SecretsSessionTokenGenerator(),
            settings.workspace_lifetime,
        ),
        get_current_workspace=GetCurrentWorkspaceHandler(unit_of_work, clock),
        check_health=CheckHealthHandler(PostgresHealthProbe(pool)),
    )


@asynccontextmanager
async def open_components(settings: Settings) -> AsyncIterator[Components]:
    """Open the connection pool for the API lifespan and close it on shutdown."""
    pool = create_pool(settings.database_url.get_secret_value())
    await pool.open()
    try:
        yield build_components(settings, pool)
    finally:
        await pool.close()


def _components(request: Request) -> Components:
    components: Components = request.app.state.components
    return components


def provide_create_workspace_handler(request: Request) -> CreateWorkspaceHandler:
    return _components(request).create_workspace


def provide_get_current_workspace_handler(request: Request) -> GetCurrentWorkspaceHandler:
    return _components(request).get_current_workspace


def provide_check_health_handler(request: Request) -> CheckHealthHandler:
    return _components(request).check_health


async def authenticate(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> WorkspacePrincipal:
    """Resolve the bearer session token to the trusted workspace principal.

    Missing, malformed and unknown tokens are indistinguishable. Expiry is checked against
    the clock on every request and never extended by activity.
    """
    components = _components(request)
    if credentials is None or not _SESSION_TOKEN.fullmatch(credentials.credentials):
        raise Unauthenticated()
    token_hash = SessionTokenHash.of(credentials.credentials)
    async with components.unit_of_work() as work:
        workspace = await work.workspaces.find_by_token_hash(token_hash)
    if workspace is None:
        raise Unauthenticated()
    if workspace.is_expired(components.clock.now()):
        raise SessionExpired()
    return WorkspacePrincipal(workspace.id)
