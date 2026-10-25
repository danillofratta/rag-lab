from rag_lab.application.exceptions.principal_required import PrincipalRequired
from rag_lab.application.exceptions.session_expired import SessionExpired
from rag_lab.application.exceptions.unauthenticated import Unauthenticated
from rag_lab.application.ports.clock import Clock
from rag_lab.application.ports.unit_of_work_factory import UnitOfWorkFactory
from rag_lab.features.get_current_workspace.query import GetCurrentWorkspaceQuery
from rag_lab.features.get_current_workspace.result import GetCurrentWorkspaceResult


class GetCurrentWorkspaceHandler:
    def __init__(self, unit_of_work: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def handle(self, query: GetCurrentWorkspaceQuery) -> GetCurrentWorkspaceResult:
        # The trusted principal is required before any persistence access.
        if query.principal is None:
            raise PrincipalRequired()
        async with self._unit_of_work() as work:
            workspace = await work.workspaces.find(query.principal.workspace_id)
        if workspace is None:
            raise Unauthenticated()
        if workspace.is_expired(self._clock.now()):
            raise SessionExpired()
        return GetCurrentWorkspaceResult(workspace.id, workspace.created_at, workspace.expires_at)
