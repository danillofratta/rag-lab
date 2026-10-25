from dataclasses import dataclass

from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId


@dataclass(frozen=True)
class WorkspacePrincipal:
    """The trusted workspace of a request, resolved from an authenticated session only."""

    workspace_id: WorkspaceId
