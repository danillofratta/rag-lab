from typing import Annotated

from fastapi import APIRouter, Depends

from rag_lab.dependencies import authenticate, provide_get_current_workspace_handler
from rag_lab.domain.workspaces.value_objects.workspace_principal import WorkspacePrincipal
from rag_lab.features.get_current_workspace.handler import GetCurrentWorkspaceHandler
from rag_lab.features.get_current_workspace.models import CurrentWorkspaceResponse
from rag_lab.features.get_current_workspace.query import GetCurrentWorkspaceQuery

router = APIRouter(tags=["workspaces"])


@router.get("/workspaces/current", response_model=CurrentWorkspaceResponse)
async def get_current_workspace(
    principal: Annotated[WorkspacePrincipal, Depends(authenticate)],
    handler: Annotated[GetCurrentWorkspaceHandler, Depends(provide_get_current_workspace_handler)],
) -> CurrentWorkspaceResponse:
    result = await handler.handle(GetCurrentWorkspaceQuery(principal))
    return CurrentWorkspaceResponse(
        workspace_id=result.workspace_id.value,
        created_at=result.created_at,
        expires_at=result.expires_at,
    )
