from dataclasses import dataclass

from rag_lab.domain.workspaces.value_objects.workspace_principal import WorkspacePrincipal


@dataclass(frozen=True)
class GetCurrentWorkspaceQuery:
    # None only when a caller bypasses authentication; the handler rejects it.
    principal: WorkspacePrincipal | None
