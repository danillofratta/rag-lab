import pytest

from tests.architecture.fixtures import feature_sources, organization, violations


@pytest.mark.parametrize("role", ["command", "query"])
def test_explicit_cqrs_requests_and_handlers_are_allowed(role):
    sources = feature_sources(role)
    assert violations(sources) == []
    assert organization(sources) == []


def test_forward_and_aliased_query_annotation_is_allowed():
    sources = feature_sources("query")
    sources["ROOT/features/sample/handler.py"] = (
        "from .query import SampleQuery as Q\n"
        "class SampleHandler:\n"
        "    async def handle(self, query: 'Q'):\n"
        "        return query\n"
    )
    assert violations(sources) == []


def test_command_may_persist_and_query_may_build_local_results():
    assert violations(feature_sources("command", "await self.repo.save(request)")) == []
    assert (
        violations(
            feature_sources("query", "results = []\nresults.append(request)\nreturn results")
        )
        == []
    )


def test_mixed_command_and_query_in_one_use_case_is_rejected():
    sources = feature_sources()
    sources["ROOT/features/sample/query.py"] = "class SampleQuery: pass"
    assert any("mixes command and query" in error for error in violations(sources))


@pytest.mark.parametrize("role,wrong", [("command", "SampleQuery"), ("query", "SampleCommand")])
def test_handler_cannot_accept_the_opposite_request_role(role, wrong):
    assert any(
        "must accept its own" in error
        for error in violations(feature_sources(role, annotation=wrong))
    )


@pytest.mark.parametrize("role", ["command", "query"])
def test_requests_cannot_implement_handler_behavior(role):
    sources = feature_sources(role)
    sources[f"ROOT/features/sample/{role}.py"] = (
        f"class Sample{role.title()}:\n    def execute(self): pass"
    )
    assert any("carry data" in error for error in violations(sources))


@pytest.mark.parametrize("signature", ["request", "request: object", "request: 'object'"])
def test_untyped_or_generic_request_handler_is_rejected(signature):
    sources = feature_sources()
    sources["ROOT/features/sample/handler.py"] = (
        f"class SampleHandler:\n    async def handle(self, {signature}): pass"
    )
    assert any("must accept its own" in error for error in violations(sources))


def test_handler_without_an_explicit_request_module_is_rejected():
    handler = "class SampleHandler:\n    async def handle(self, request): pass"
    sources = {"ROOT/features/sample/handler.py": handler}
    assert any("exactly one request module" in error for error in violations(sources))


def test_handle_must_be_async():
    sources = feature_sources()
    path = "ROOT/features/sample/handler.py"
    sources[path] = sources[path].replace("async def", "def")
    assert any("must be async" in error for error in violations(sources))


@pytest.mark.parametrize(
    "write",
    [
        "await self.repository.save(request)",
        "await self.uow.commit()",
        "await self.gateway.publish(request)",
        "await self.queue.enqueue(request)",
        "self.state = request",
        "self.state['count'] = 0",
    ],
)
def test_query_writes_and_dispatch_are_rejected(write):
    assert any("CQRS query" in error for error in violations(feature_sources("query", write)))


@pytest.mark.parametrize(
    "dependency",
    [
        "from ..other.handler import OtherHandler",
        "from ROOT.features.other.handler import OtherHandler as H",
        "import ROOT.features.other.handler as handlers",
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n from ..other.handler import OtherHandler",
        "from ..other import handler as other_handler",
    ],
)
def test_cross_slice_and_direct_handler_dependencies_are_rejected(dependency):
    sources = feature_sources()
    path = "ROOT/features/sample/handler.py"
    sources[path] = dependency + "\n" + sources[path]
    errors = violations(sources)
    assert any("sibling slice" in error for error in errors)
    assert any("direct feature handler" in error for error in errors)


def test_slice_prefix_cannot_be_used_to_import_a_neighbor():
    sources = feature_sources()
    sources["ROOT/features/sample/handler.py"] += (
        "\nfrom ROOT.features.sample_extra.command import ExtraCommand"
    )
    assert any("inward application imports" in error for error in violations(sources))


@pytest.mark.parametrize("path", ["ROOT/endpoint.py", "ROOT/controllers/sample.py", "ROOT/main.py"])
def test_endpoints_cannot_escape_their_feature(path):
    errors = organization({path: "@router.post('/workspaces')\ndef create(): pass"})
    assert any("endpoints belong" in error for error in errors)
