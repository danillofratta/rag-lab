from datetime import timedelta

from rag_lab.application.ports.clock import Clock
from rag_lab.application.ports.session_token_generator import SessionTokenGenerator
from rag_lab.application.ports.unit_of_work_factory import UnitOfWorkFactory
from rag_lab.application.ports.workspace_id_generator import WorkspaceIdGenerator
from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.domain.workspaces.entities.workspace import Workspace
from rag_lab.features.create_workspace.command import CreateWorkspaceCommand
from rag_lab.features.create_workspace.result import CreateWorkspaceResult


class CreateWorkspaceHandler:
    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        clock: Clock,
        workspace_ids: WorkspaceIdGenerator,
        session_tokens: SessionTokenGenerator,
        lifetime: timedelta,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._workspace_ids = workspace_ids
        self._session_tokens = session_tokens
        self._lifetime = lifetime

    async def handle(self, command: CreateWorkspaceCommand) -> CreateWorkspaceResult:
        token = self._session_tokens.next_token()
        workspace = Workspace.create(
            self._workspace_ids.next_id(),
            SessionTokenHash.of(token),
            self._clock.now(),
            self._lifetime,
        )
        async with self._unit_of_work() as work:
            await work.workspaces.add(workspace)
            await work.commit()
        return CreateWorkspaceResult(
            workspace.id, token, workspace.created_at, workspace.expires_at
        )
