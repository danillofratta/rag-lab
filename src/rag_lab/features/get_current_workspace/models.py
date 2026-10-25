from datetime import datetime

from pydantic import BaseModel


class CurrentWorkspaceResponse(BaseModel):
    workspace_id: str
    created_at: datetime
    expires_at: datetime
