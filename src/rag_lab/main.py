from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI

from rag_lab.components import ComponentsOpener
from rag_lab.dependencies import open_components
from rag_lab.features.check_health.endpoint import router as check_health_router
from rag_lab.features.create_workspace.endpoint import router as create_workspace_router
from rag_lab.features.get_current_workspace.endpoint import (
    router as get_current_workspace_router,
)
from rag_lab.infrastructure.settings.load_settings import load_settings
from rag_lab.infrastructure.settings.settings import Settings
from rag_lab.transport.body_limit_middleware import BodyLimitMiddleware
from rag_lab.transport.configure_logging import configure_logging
from rag_lab.transport.register_error_handlers import register_error_handlers
from rag_lab.transport.request_context_middleware import RequestContextMiddleware


def create_app(settings: Settings | None = None, opener: ComponentsOpener | None = None) -> FastAPI:
    """Build the API: settings, resources, middleware, error handling and feature routers."""
    active = settings or load_settings()
    open_resources = opener or partial(open_components, active)
    configure_logging(active.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with open_resources() as components:
            app.state.components = components
            yield

    docs = active.docs_enabled
    app = FastAPI(
        title="RAG Lab",
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    register_error_handlers(app)
    app.add_middleware(BodyLimitMiddleware, max_bytes=active.max_body_bytes)
    # Added last, so it is outermost: it identifies and logs every request, including refusals.
    app.add_middleware(RequestContextMiddleware)
    app.include_router(check_health_router)
    app.include_router(create_workspace_router)
    app.include_router(get_current_workspace_router)
    return app
