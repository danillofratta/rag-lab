from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateWorkspaceRequest(BaseModel):
    """Workspace creation takes no input; unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


class CreateWorkspaceResponse(BaseModel):
    workspace_id: str
    session_token: str
    created_at: datetime
    expires_at: datetime
