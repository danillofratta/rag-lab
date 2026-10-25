from dataclasses import dataclass
from datetime import datetime

from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId


@dataclass(frozen=True)
class GetCurrentWorkspaceResult:
    workspace_id: WorkspaceId
    created_at: datetime
    expires_at: datetime
