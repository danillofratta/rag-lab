from typing import Annotated

from fastapi import APIRouter, Depends

from rag_lab.dependencies import provide_create_workspace_handler
from rag_lab.features.create_workspace.command import CreateWorkspaceCommand
from rag_lab.features.create_workspace.handler import CreateWorkspaceHandler
from rag_lab.features.create_workspace.models import (
    CreateWorkspaceRequest,
    CreateWorkspaceResponse,
)

router = APIRouter(tags=["workspaces"])


@router.post("/workspaces", status_code=201, response_model=CreateWorkspaceResponse)
async def create_workspace(
    handler: Annotated[CreateWorkspaceHandler, Depends(provide_create_workspace_handler)],
    body: CreateWorkspaceRequest | None = None,
) -> CreateWorkspaceResponse:
    result = await handler.handle(CreateWorkspaceCommand())
    return CreateWorkspaceResponse(
        workspace_id=result.workspace_id.value,
        session_token=result.session_token,
        created_at=result.created_at,
        expires_at=result.expires_at,
    )
