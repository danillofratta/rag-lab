import pytest

from tests.architecture.fixtures import violations

IMPORT_FORMS = [
    "import {name}",
    "import {name} as framework",
    "from {name} import graph",
    "from {name} import graph as g",
    "from {name}.sub import graph",
    "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n import {name}",
]


def forms(name):
    return [form.format(name=name) for form in IMPORT_FORMS]


@pytest.mark.parametrize("source", forms("langgraph"))
@pytest.mark.parametrize(
    "path",
    [
        "ROOT/features/ask/handler.py",
        "ROOT/features/ask/nodes.py",
        "ROOT/features/ask/command.py",
        "ROOT/features/ask/endpoint.py",
        "ROOT/infrastructure/runtime/graph.py",
        "ROOT/dependencies.py",
        "ROOT/domain/rag/entities/run.py",
    ],
)
def test_langgraph_is_rejected_outside_workflow(path, source):
    assert any("langgraph confined" in error for error in violations({path: source}))


@pytest.mark.parametrize("source", forms("langgraph"))
def test_langgraph_is_allowed_in_feature_workflow(source):
    assert violations({"ROOT/features/ask/workflow.py": source}) == []


def test_langgraph_is_rejected_when_re_exported_through_a_package_initializer():
    sources = {"ROOT/features/ask/__init__.py": "from langgraph.graph import StateGraph"}
    assert any("langgraph confined" in error for error in violations(sources))


def test_workflow_still_rejects_other_third_party_and_infrastructure():
    assert violations({"ROOT/features/ask/workflow.py": "import httpx"})
    assert violations({"ROOT/features/ask/workflow.py": "from ROOT.infrastructure import x"})


@pytest.mark.parametrize("source", forms("pydantic") + ["from pydantic_settings import X"])
@pytest.mark.parametrize(
    "path",
    [
        "ROOT/features/ask/handler.py",
        "ROOT/features/ask/nodes.py",
        "ROOT/features/ask/command.py",
        "ROOT/features/ask/query.py",
        "ROOT/features/ask/result.py",
        "ROOT/features/ask/endpoint.py",
        "ROOT/domain/shared/value_objects/workspace_id.py",
        "ROOT/application/ports/clock.py",
        "ROOT/dependencies.py",
        "ROOT/transport/errors.py",
    ],
)
def test_pydantic_is_rejected_outside_models_and_infrastructure(path, source):
    assert any("pydantic confined" in error for error in violations({path: source}))


@pytest.mark.parametrize("source", forms("pydantic") + ["from pydantic_settings import X"])
@pytest.mark.parametrize(
    "path", ["ROOT/features/ask/models.py", "ROOT/infrastructure/settings/settings.py"]
)
def test_pydantic_is_allowed_in_models_and_infrastructure(path, source):
    assert violations({path: source}) == []


@pytest.mark.parametrize(
    "path",
    [
        "ROOT/features/ask/handler.py",
        "ROOT/features/ask/models.py",
        "ROOT/infrastructure/runtime/x.py",
        "ROOT/domain/shared/entities/x.py",
    ],
)
def test_web_framework_is_rejected_outside_http_adapters(path):
    for source in ("import fastapi", "from fastapi import APIRouter", "import starlette"):
        assert any("web framework" in error for error in violations({path: source}))


@pytest.mark.parametrize(
    "path",
    [
        "ROOT/features/ask/endpoint.py",
        "ROOT/transport/errors.py",
        "ROOT/dependencies.py",
        "ROOT/main.py",
    ],
)
def test_web_framework_is_allowed_in_http_adapters_and_bootstrap(path):
    assert violations({path: "from fastapi import APIRouter\nimport starlette"}) == []


@pytest.mark.parametrize(
    "source",
    [
        "from ROOT.domain.rag.entities import run",
        "import ROOT.domain.rag.entities.run as run",
        "from ...rag.entities import run",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n from ROOT.domain.rag import x",
    ],
)
@pytest.mark.parametrize(
    "path", ["ROOT/domain/shared/value_objects/x.py", "ROOT/domain/workspaces/entities/x.py"]
)
def test_inner_domain_packages_cannot_import_the_rag_package(path, source):
    assert any("domain package order" in error for error in violations({path: source}))


@pytest.mark.parametrize(
    "source",
    ["from ROOT.domain.workspaces import x", "from ...workspaces.entities import workspace"],
)
def test_shared_cannot_import_workspaces(source):
    path = "ROOT/domain/shared/value_objects/x.py"
    assert any("domain package order" in error for error in violations({path: source}))


def test_domain_package_order_allows_outer_packages_to_import_inner_ones():
    sources = {
        "ROOT/domain/rag/entities/run.py": (
            "from ROOT.domain.workspaces.value_objects import workspace_id\n"
            "from ROOT.domain.shared.value_objects import identifier"
        ),
        "ROOT/domain/workspaces/entities/workspace.py": (
            "from ROOT.domain.shared.value_objects import identifier"
        ),
        "ROOT/domain/shared/value_objects/identifier.py": "import re",
    }
    assert violations(sources) == []


@pytest.mark.parametrize(
    "source",
    [
        "import ROOT",
        "from ROOT import features",
        "import ROOT.domain as core",
        "from ROOT.features.ask import command",
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n import ROOT.dependencies",
    ],
)
def test_ui_cannot_import_the_package(source):
    assert any("ui imports" in error for error in violations({"ui/app.py": source}))


def test_ui_may_use_third_party_and_standard_library_modules():
    assert violations({"ui/app.py": "import streamlit\nimport httpx\nimport json"}) == []


@pytest.mark.parametrize(
    "source",
    [
        "from ROOT.infrastructure.repositories import x",
        "from ROOT.domain.rag.entities import run",
        "import ROOT.application.ports.clock",
        "from ROOT.features.ask.endpoint import router",
        "from ROOT.features.ask.nodes import AskNodes",
    ],
)
def test_evaluation_cannot_reach_internals(source):
    assert any("evaluation entry" in error for error in violations({"eval/runners/run.py": source}))


@pytest.mark.parametrize(
    "source",
    [
        "from ROOT.dependencies import build_components",
        "from ROOT.features.ask.command import AskQuestionCommand",
        "from ROOT.features.ask.handler import AskQuestionHandler",
        "from ROOT.features.ask.result import AskQuestionResult",
        "from ROOT.features.ask import handler",
    ],
)
def test_evaluation_may_use_the_composition_root_and_feature_requests(source):
    assert violations({"eval/runners/run.py": source}) == []
