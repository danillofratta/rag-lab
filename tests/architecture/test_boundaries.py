import ast

import pytest

from tests.architecture import rules
from tests.architecture.fixtures import (
    REPOSITORY,
    fixture,
    organization,
    real_sources,
    violations,
)


def test_actual_package_dependencies_point_inward():
    sources = real_sources()
    assert rules.inspect_sources(sources) == []
    assert rules.inspect_organization(sources) == []


def test_no_obsolete_or_centralized_endpoint_directories():
    root = REPOSITORY / "src" / rules.ROOT
    assert not (root / "api").exists()
    assert not (root / "application" / "features").exists()
    assert not any(path.name in {"routes", "controllers"} for path in root.rglob("*"))
    assert not list((root / "application" / "ports").glob("*repository.py"))


def test_bootstrap_defines_no_classes():
    path = REPOSITORY / "src" / rules.ROOT / "main.py"
    if not path.exists():
        pytest.skip("main.py arrives with the API runtime task")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))


@pytest.mark.parametrize(
    "path,source,expected",
    [
        ("ROOT/api/routes/workspaces.py", "", "centralized endpoint"),
        ("ROOT/controllers/workspaces.py", "", "centralized endpoint"),
        ("ROOT/endpoints/create.py", "router = APIRouter()", "routers belong"),
        ("ROOT/main.py", "@app.post('/workspaces')\ndef create(): pass", "endpoints belong"),
        ("ROOT/main.py", "app.add_api_route('/workspaces', handler)", "endpoints belong"),
        (
            "ROOT/application/ports/workspace_repository.py",
            "from typing import Protocol\nclass WorkspaceRepository(Protocol): pass",
            "domain/repositories",
        ),
        ("ROOT/features/create_workspace/models.py", "class Workspace: pass", "only HTTP schemas"),
        (
            "ROOT/domain/shared/value_objects/workspace_id.py",
            "class WorkspaceId: pass\nclass Other: pass",
            "one class per file",
        ),
        (
            "ROOT/domain/workspaces/policies/expiry_policy.py",
            "class ExpiryPolicy: pass\nclass Other: pass",
            "one class per file",
        ),
        ("ROOT/domain/workspaces/entities/wrong.py", "class Workspace: pass", "workspace.py"),
        ("ROOT/domain/workspaces/entities/__init__.py", "class Workspace: pass", "workspace.py"),
        (
            "ROOT/domain/shared/value_objects/models.py",
            "class WorkspaceId: pass",
            "grouped generic",
        ),
        ("ROOT/domain/helpers/x.py", "", "unknown domain package"),
        ("ROOT/domain/shared/helpers/x.py", "", "unknown domain package folder"),
        ("ROOT/domain/shared/x.py", "", "role folders"),
        ("ROOT/domain/x.py", "", "packages only"),
    ],
)
def test_layout_negative_fixtures(path, source, expected):
    assert any(expected in issue for issue in organization({path: source}))


def test_feature_local_http_grouping_and_endpoint_are_allowed():
    schemas = (
        "from pydantic import BaseModel\nclass One(BaseModel): pass\nclass Two(BaseModel): pass"
    )
    endpoint = "router = APIRouter()\n@router.post('/workspaces')\ndef create(): pass"
    feature = "ROOT/features/create_workspace/"
    assert (
        organization(
            {
                feature + "models.py": schemas,
                feature + "endpoint.py": endpoint,
                feature + "command.py": "class CreateWorkspaceCommand: pass",
                feature + "handler.py": "class CreateWorkspaceHandler: pass",
                feature + "nodes.py": "class A: pass\nclass B: pass",
            }
        )
        == []
    )


@pytest.mark.parametrize(
    "source",
    [
        "from fastapi import Request",
        "import pydantic as schemas",
        "from .models import CreateBody",
        "from .endpoint import router",
        "from .job import run",
        "from .workflow import build",
    ],
)
def test_handlers_cannot_import_adapters_even_from_their_own_slice(source):
    assert violations({"ROOT/features/create_workspace/handler.py": source})


@pytest.mark.parametrize(
    "path,source,rule",
    [
        ("ROOT/domain/shared/entities/x.py", "import pydantic as validation", "domain purity"),
        ("ROOT/domain/shared/entities/x.py", "import sqlite3", "domain I/O"),
        ("ROOT/domain/shared/entities/x.py", "import asyncio", "domain I/O"),
        ("ROOT/domain/shared/entities/x.py", "from os import environ as env", "domain I/O"),
        (
            "ROOT/domain/shared/entities/x.py",
            "from datetime import datetime as dt\ndt.now()",
            "clock",
        ),
        (
            "ROOT/domain/shared/entities/x.py",
            "from ....infrastructure import store",
            "domain purity",
        ),
        (
            "ROOT/features/create_workspace/handler.py",
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n from ROOT.transport import app",
            "inward application",
        ),
        (
            "ROOT/application/ports/__init__.py",
            "from ROOT.infrastructure import persistence as exported",
            "inward application",
        ),
        (
            "ROOT/features/create_workspace/handler.py",
            "from ..get_current_workspace import handler",
            "sibling slice",
        ),
        (
            "ROOT/infrastructure/repositories/x.py",
            "from ROOT.features.create_workspace import handler",
            "adapter depends",
        ),
        ("ROOT/infrastructure/repositories/x.py", "import ROOT.dependencies", "adapter depends"),
        (
            "ROOT/features/create_workspace/endpoint.py",
            "from ROOT.infrastructure import persistence",
            "outside composition",
        ),
        ("ROOT/features/create_workspace/endpoint.py", "db.execute('SELECT 1')", "SQL outside"),
        ("ROOT/features/create_workspace/handler.py", "db.execute('SELECT 1')", "SQL outside"),
        (
            "ROOT/features/create_workspace/handler.py",
            "container.resolve('db')",
            "hidden dependency",
        ),
        ("ROOT/features/create_workspace/handler.py", "services = {}", "mutable application"),
        ("ROOT/features/create_workspace/handler.py", "Depends(get_db)", "hidden dependency"),
        ("ROOT/domain/shared/entities/x.py", "eval('bad')", "dynamic execution"),
        (
            "ROOT/features/create_workspace/endpoint.py",
            "import importlib\nimportlib.import_module('x')",
            "dynamic import",
        ),
        ("ROOT/__init__.py", "from ROOT.domain import shared", "root re-export"),
        (
            "ROOT/features/create_workspace/models.py",
            "from ROOT.infrastructure import x",
            "outside",
        ),
        ("ROOT/transport/errors.py", "from ROOT.features.x import endpoint", "transport depends"),
        ("ROOT/main.py", "from ROOT.domain.shared import entities", "bootstrap imports"),
        ("ROOT/main.py", "from ROOT.features.x.handler import XHandler", "bootstrap imports"),
        ("ROOT/components.py", "from ROOT.infrastructure.repositories import x", "outside"),
    ],
)
def test_architecture_negative_fixtures(path, source, rule):
    assert any(rule in violation for violation in violations({path: source}))


def test_composition_bootstrap_and_own_slice_are_allowed():
    assert (
        violations(
            {
                "ROOT/dependencies.py": "from ROOT.infrastructure import persistence",
                "ROOT/components.py": "from ROOT.infrastructure.settings import settings",
                "ROOT/main.py": (
                    "from ROOT.infrastructure.settings.settings import Settings\n"
                    "from ROOT.dependencies import build\n"
                    "from ROOT.features.create_workspace import endpoint\n"
                    "from ROOT.features.create_workspace.endpoint import router\n"
                    "from ROOT.transport import errors"
                ),
                "ROOT/transport/errors.py": "from ROOT.application.exceptions import x",
                "ROOT/features/create_workspace/handler.py": (
                    "from .command import CreateWorkspaceCommand"
                ),
            }
        )
        == []
    )


def test_dependency_cycle_is_rejected():
    result = violations(
        {
            "ROOT/domain/shared/a.py": "from .b import v",
            "ROOT/domain/shared/b.py": "from .a import v",
        }
    )
    assert any("cycle" in violation for violation in result)


def test_feature_modules_must_be_role_files():
    assert any(
        "role files" in issue
        for issue in violations({"ROOT/features/create_workspace/harness.py": "x = 1"})
    )
    assert any(
        "role files" in issue
        for issue in violations({"ROOT/features/create_workspace/sub/handler.py": "x = 1"})
    )
    assert not violations({"ROOT/features/create_workspace/job.py": "x = 1"})


def test_fixture_helper_keeps_the_root_constant_single():
    assert fixture({"ROOT/a.py": "import ROOT.b"}) == {
        f"{rules.ROOT}/a.py": f"import {rules.ROOT}.b"
    }
