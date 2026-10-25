from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from rag_lab.dependencies import provide_check_health_handler
from rag_lab.features.check_health.handler import CheckHealthHandler
from rag_lab.features.check_health.models import LiveResponse, ReadyResponse
from rag_lab.features.check_health.query import CheckHealthQuery

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LiveResponse)
async def live() -> LiveResponse:
    """Liveness: the process can serve requests. Checks no dependency."""
    return LiveResponse(status="ok")


@router.get("/health/ready", response_model=ReadyResponse, responses={503: {"model": ReadyResponse}})
async def ready(
    handler: Annotated[CheckHealthHandler, Depends(provide_check_health_handler)],
) -> JSONResponse:
    """Readiness: dependencies reachable and schema current. Names and statuses only."""
    result = await handler.handle(CheckHealthQuery())
    body = ReadyResponse(
        status="ready" if result.ready else "not_ready",
        dependencies={
            name: "ready" if is_ready else "not_ready"
            for name, is_ready in result.dependencies.items()
        },
    )
    return JSONResponse(body.model_dump(), status_code=200 if result.ready else 503)
