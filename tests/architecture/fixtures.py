"""Helpers shared by the architecture tests.

Fixtures are written with the placeholder ``ROOT`` so the root package name stays a single
constant in ``rules.py``.
"""

from pathlib import Path
from textwrap import indent

from tests.architecture import rules

REPOSITORY = Path(__file__).resolve().parents[2]


def fx(text):
    return text.replace("ROOT", rules.ROOT)


def fixture(sources):
    return {fx(path): fx(source) for path, source in sources.items()}


def violations(sources):
    return rules.inspect_sources(fixture(sources))


def organization(sources):
    return rules.inspect_organization(fixture(sources))


def real_sources():
    """Project sources keyed like the fixtures: package files under src, plus ui and eval."""
    sources = {}
    for base, roots in ((REPOSITORY / "src", [rules.ROOT]), (REPOSITORY, ["ui", "eval"])):
        for name in roots:
            for path in (base / name).rglob("*.py"):
                sources[path.relative_to(base).as_posix()] = path.read_text(encoding="utf-8")
    return sources


def feature_sources(role="command", body="return None", annotation=None, name="sample"):
    """A minimal valid slice with one async request handler."""
    request = name.title().replace("_", "") + role.title()
    return {
        f"ROOT/features/{name}/{role}.py": f"class {request}: pass",
        f"ROOT/features/{name}/handler.py": (
            f"from .{role} import {request}\n"
            f"class {name.title()}Handler:\n"
            f"    async def handle(self, request: {annotation or request}):\n"
            + indent(body, "        ")
        ),
    }
