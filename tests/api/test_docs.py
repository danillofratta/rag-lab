import pytest

DOCUMENTATION_ROUTES = ["/docs", "/redoc", "/openapi.json"]


@pytest.mark.anyio
@pytest.mark.parametrize("route", DOCUMENTATION_ROUTES)
async def test_documentation_is_served_when_enabled(docs_harness, route):
    async with docs_harness.client() as client:
        assert (await client.get(route)).status_code == 200


@pytest.mark.anyio
@pytest.mark.parametrize("route", DOCUMENTATION_ROUTES)
async def test_documentation_is_not_found_when_disabled(client, route):
    assert (await client.get(route)).status_code == 404
