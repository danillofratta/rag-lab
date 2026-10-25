import ast

from tests.architecture import rules
from tests.architecture.fixtures import REPOSITORY

PACKAGE = REPOSITORY / "src" / rules.ROOT

# Packages from the AGENTS.md tree that exist in the foundation change. worker.py, ui/, eval/
# and pipelines/ arrive with their own changes.
EXPECTED_PACKAGES = {
    "domain",
    "domain/shared",
    "domain/workspaces",
    "domain/rag",
    "application",
    "application/ports",
    "application/ports/rag",
    "application/exceptions",
    "features",
    "infrastructure",
    "infrastructure/repositories",
    "infrastructure/persistence",
    "infrastructure/gateways",
    "infrastructure/gateways/vector_index",
    "infrastructure/gateways/llm",
    "infrastructure/gateways/tracing",
    "infrastructure/strategies",
    "infrastructure/pipelines",
    "infrastructure/settings",
    "infrastructure/runtime",
    "transport",
}


def test_every_package_in_the_agents_tree_exists():
    for name in EXPECTED_PACKAGES:
        assert (PACKAGE / name / "__init__.py").is_file(), name


def test_no_package_outside_the_agents_tree_exists_except_feature_slices_and_role_folders():
    allowed_roles = rules.DOMAIN_FOLDERS | {"migrations"}
    for init in PACKAGE.rglob("__init__.py"):
        folder = init.parent.relative_to(PACKAGE).as_posix()
        if folder in {".", ""} or folder in EXPECTED_PACKAGES:
            continue
        parts = folder.split("/")
        in_domain_role = parts[0] == "domain" and parts[-1] in allowed_roles
        in_feature = parts[0] == "features" and len(parts) == 2
        in_adapter_kind = parts[0] == "infrastructure" and parts[1] in {"gateways", "strategies"}
        assert in_domain_role or in_feature or in_adapter_kind, folder


def test_initializers_define_no_classes():
    for init in PACKAGE.rglob("__init__.py"):
        tree = ast.parse(init.read_text(encoding="utf-8"))
        assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree)), init
