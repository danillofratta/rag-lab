from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from rag_lab.application.ports.clock import Clock
from rag_lab.application.ports.unit_of_work_factory import UnitOfWorkFactory
from rag_lab.features.check_health.handler import CheckHealthHandler
from rag_lab.features.create_workspace.handler import CreateWorkspaceHandler
from rag_lab.features.get_current_workspace.handler import GetCurrentWorkspaceHandler
from rag_lab.infrastructure.settings.settings import Settings


@dataclass(frozen=True)
class Components:
    """Everything the API needs at request time, built once by the composition root."""

    settings: Settings
    clock: Clock
    unit_of_work: UnitOfWorkFactory
    create_workspace: CreateWorkspaceHandler
    get_current_workspace: GetCurrentWorkspaceHandler
    check_health: CheckHealthHandler


# Opens the resources behind the components for the lifetime of the API process.
ComponentsOpener = Callable[[], AbstractAsyncContextManager[Components]]
