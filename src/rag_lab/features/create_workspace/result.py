from dataclasses import dataclass, field
from datetime import datetime

from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId


@dataclass(frozen=True)
class CreateWorkspaceResult:
    workspace_id: WorkspaceId
    # The only time the token exists in clear text; keep it out of repr and logs.
    session_token: str = field(repr=False)
    created_at: datetime
    expires_at: datetime
