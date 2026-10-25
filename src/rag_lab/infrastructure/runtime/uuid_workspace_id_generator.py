from uuid import uuid4

from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId


class UuidWorkspaceIdGenerator:
    def next_id(self) -> WorkspaceId:
        return WorkspaceId(str(uuid4()))
