import pytest

from tests.architecture.fixtures import feature_sources, organization, violations

REPOSITORY_CONTRACT = "ROOT/domain/workspaces/repositories/workspace_repository.py"
HANDLER = "ROOT/features/sample/handler.py"


def injected_sources(annotation="WorkspaceRepository", default=""):
    sources = feature_sources()
    sources[REPOSITORY_CONTRACT] = (
        "from typing import Protocol as Contract\n"
        "class WorkspaceRepository(Contract):\n    async def save(self, workspace): ..."
    )
    sources[HANDLER] = (
        "from .command import SampleCommand\n"
        "from ROOT.domain.workspaces.repositories.workspace_repository import WorkspaceRepository\n"
        "class SampleHandler:\n"
        f"    def __init__(self, repository: {annotation}{default}):\n"
        "        self.repository = repository\n"
        "    async def handle(self, request: SampleCommand):\n"
        "        await self.repository.save(request)\n"
    )
    return sources


def test_typed_constructor_injection_and_aliased_protocol_are_allowed():
    sources = injected_sources()
    assert violations(sources) == []
    assert organization(sources) == []


@pytest.mark.parametrize("annotation", ["object", "'object'", "Any"])
def test_untyped_collaborators_are_rejected(annotation):
    errors = violations(injected_sources(annotation))
    assert any("constructor collaborators" in error for error in errors)


@pytest.mark.parametrize("default", [" = WorkspaceRepository()", " = global_repository"])
def test_constructors_cannot_capture_default_dependencies(default):
    errors = violations(injected_sources(default=default))
    assert any("hidden default" in error for error in errors)


def test_explicit_optional_port_can_be_injected_without_constructing_a_fallback():
    assert violations(injected_sources(default=" = None")) == []


def test_plain_values_and_lifetimes_can_be_injected():
    sources = injected_sources()
    sources[HANDLER] = (
        sources[HANDLER]
        .replace(
            "repository: WorkspaceRepository",
            "repository: WorkspaceRepository, lifetime: timedelta",
        )
        .replace("from .command", "from datetime import timedelta\nfrom .command")
    )
    assert violations(sources) == []


@pytest.mark.parametrize("role", ["nodes", "workflow"])
def test_nodes_and_workflows_use_constructor_injection_too(role):
    sources = injected_sources()
    body = (
        "from ROOT.domain.workspaces.repositories.workspace_repository import WorkspaceRepository\n"
        "class SampleThing:\n"
        "    def __init__(self, repository: {annotation}):\n"
        "        self.repository = repository\n"
    )
    path = f"ROOT/features/sample/{role}.py"
    sources[path] = body.format(annotation="WorkspaceRepository")
    assert violations(sources) == []
    sources[path] = body.format(annotation="object")
    assert any("constructor collaborators" in error for error in violations(sources))


def test_workflow_may_receive_its_own_nodes_but_nodes_may_not_receive_a_workflow():
    sources = feature_sources()
    sources["ROOT/features/sample/nodes.py"] = "class SampleNodes: pass"
    sources["ROOT/features/sample/workflow.py"] = (
        "from .nodes import SampleNodes\n"
        "class SampleWorkflow:\n    def __init__(self, nodes: SampleNodes): ..."
    )
    assert violations(sources) == []
    sources["ROOT/features/sample/nodes.py"] = (
        "from .workflow import SampleWorkflow\n"
        "class SampleNodes:\n    def __init__(self, flow: SampleWorkflow): ..."
    )
    assert any("constructor collaborators" in error for error in violations(sources))


@pytest.mark.parametrize(
    "hidden",
    [
        "container = dict()",
        "services = {}",
        "registry = SimpleNamespace()",
        "global_dependencies = SimpleNamespace()",
        "repository = container.get('repository')",
        "repository = service_locator.get('repository')",
        "repository = get_repository()",
        "repository = get_components()",
        "from fastapi import Depends as Inject\nrepository = Inject(get_repository)",
    ],
)
def test_hidden_dependency_resolution_and_framework_di_are_rejected(hidden):
    sources = injected_sources()
    sources[HANDLER] += "\n" + hidden
    assert violations(sources)


@pytest.mark.parametrize(
    "constructor",
    [
        "PostgresWorkspaceRepository",
        "LocalCredentialGateway",
        "WorkspaceRepository",
        "RecursiveChunkerStrategy",
        "UuidWorkspaceIdGenerator",
    ],
)
@pytest.mark.parametrize("role", ["handler", "nodes", "workflow", "endpoint", "job"])
def test_slices_cannot_construct_collaborators(constructor, role):
    sources = injected_sources()
    path = f"ROOT/features/sample/{role}.py"
    sources[path] = sources.get(path, "") + f"\nrepository = {constructor}()"
    assert any("constructed outside composition" in error for error in violations(sources))


def test_handler_cannot_replace_injected_port_with_a_concrete_adapter():
    sources = injected_sources()
    sources[HANDLER] = sources[HANDLER].replace(
        "self.repository = repository", "self.repository = PostgresWorkspaceRepository(connection)"
    )
    assert any("constructed outside composition" in error for error in violations(sources))


def test_adapter_construction_is_allowed_only_at_the_composition_root():
    source = (
        "from ROOT.infrastructure.repositories.postgres_workspace_repository "
        "import PostgresWorkspaceRepository as Adapter\nrepository = Adapter(connection)"
    )
    assert violations({"ROOT/dependencies.py": source}) == []
    for path in (HANDLER, "ROOT/components.py", "ROOT/main.py"):
        assert violations({path: source})


@pytest.mark.parametrize(
    "import_statement",
    [
        "import fastapi",
        "from fastapi import Request as HTTPRequest",
        "import pydantic as validation",
        "from sqlalchemy.orm import Session",
        "import ROOT.infrastructure.persistence.database as db",
        "from ....infrastructure import persistence",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n import sqlalchemy",
    ],
)
def test_domain_cannot_import_frameworks_or_adapters(import_statement):
    errors = violations({"ROOT/domain/workspaces/entities/workspace.py": import_statement})
    assert any("domain purity" in error for error in errors)


def test_domain_prefix_does_not_allow_other_packages():
    assert violations({"ROOT/domain/workspaces/entities/x.py": "import ROOT.domain_extra.adapter"})


@pytest.mark.parametrize(
    "path,source,expected",
    [
        (
            "ROOT/application/ports/workspace_repository.py",
            "from typing import Protocol\nclass WorkspaceRepository(Protocol): pass",
            "domain/repositories",
        ),
        (
            "ROOT/domain/workspaces/repositories/credential_gateway.py",
            "from typing import Protocol\nclass CredentialGateway(Protocol): pass",
            "application/ports",
        ),
        ("ROOT/infrastructure/gateways/credential.py", "class Credential: pass", "Gateway suffix"),
        (
            "ROOT/infrastructure/security/local_credential_gateway.py",
            "class LocalCredentialGateway: pass",
            "infrastructure/gateways",
        ),
        (
            "ROOT/infrastructure/gateways/postgres_workspace_repository.py",
            "class PostgresWorkspaceRepository: pass",
            "infrastructure/repositories",
        ),
        (
            "ROOT/infrastructure/gateways/base_gateway.py",
            "class BaseGateway: pass",
            "generic adapter",
        ),
        (
            "ROOT/application/ports/chunker_strategy.py",
            "from typing import Protocol\nclass ChunkerStrategy(Protocol): pass",
            "ports/rag",
        ),
        (
            "ROOT/application/ports/i_clock.py",
            "from typing import Protocol\nclass IClock(Protocol): pass",
            "generic port",
        ),
        (
            "ROOT/application/ports/misc_helper.py",
            "from typing import Protocol\nclass MiscHelper(Protocol): pass",
            "express responsibility",
        ),
        (
            "ROOT/application/ports/rag/misc_helper.py",
            "from typing import Protocol\nclass MiscHelper(Protocol): pass",
            "express responsibility",
        ),
        (
            "ROOT/domain/workspaces/repositories/workspace_store.py",
            "from typing import Protocol\nclass WorkspaceStore(Protocol): pass",
            "require Repository",
        ),
        (
            "ROOT/domain/workspaces/repositories/workspace_repository.py",
            "class WorkspaceRepository: pass",
            "Protocol or ABC",
        ),
    ],
)
def test_contract_and_adapter_conventions(path, source, expected):
    assert any(expected in error for error in organization({path: source}))


def test_contract_and_adapter_naming_is_allowed():
    sources = {
        "ROOT/application/ports/clock.py": "from typing import Protocol\nclass Clock(Protocol): ...",
        "ROOT/application/ports/job_queue_gateway.py": (
            "from typing import Protocol\nclass JobQueueGateway(Protocol): ..."
        ),
        "ROOT/application/ports/rag/chunker_strategy.py": (
            "from typing import Protocol\nclass ChunkerStrategy(Protocol): ..."
        ),
        "ROOT/application/ports/rag/strategy_registry.py": (
            "from abc import ABC\nclass StrategyRegistry(ABC): ..."
        ),
        "ROOT/domain/workspaces/repositories/workspace_repository.py": (
            "from typing import Protocol\nclass WorkspaceRepository(Protocol): ..."
        ),
        "ROOT/infrastructure/gateways/queue/arq_job_queue_gateway.py": (
            "class ArqJobQueueGateway:\n async def enqueue(self): pass"
        ),
        "ROOT/infrastructure/repositories/postgres_workspace_repository.py": (
            "class PostgresWorkspaceRepository:\n async def save(self): pass"
        ),
        "ROOT/infrastructure/strategies/chunker/recursive_chunker.py": "class RecursiveChunker: ...",
    }
    assert violations(sources) == []
    assert organization(sources) == []


@pytest.mark.parametrize(
    "path,source",
    [
        (
            "ROOT/domain/workspaces/repositories/workspace_repository.py",
            "from typing import Protocol\nclass WorkspaceRepository(Protocol):\n"
            "    def save(self): ...",
        ),
        (
            "ROOT/application/ports/rag/llm_gateway.py",
            "from typing import Protocol\nclass LlmGateway(Protocol):\n    def complete(self): ...",
        ),
        (
            "ROOT/application/ports/health_probe.py",
            "from typing import Protocol\nclass HealthProbe(Protocol):\n    def check(self): ...",
        ),
    ],
)
def test_io_contracts_must_be_async(path, source):
    assert any("must be async" in error for error in violations({path: source}))
