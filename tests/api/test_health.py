import pytest


@pytest.mark.anyio
async def test_liveness_is_200_even_when_the_database_is_down(client, harness):
    harness.probe.status = {"database": False}
    response = await client.get("/health/live")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_readiness_is_200_and_lists_the_database_when_ready(client):
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "dependencies": {"database": "ready"}}


@pytest.mark.anyio
async def test_readiness_is_503_without_details_when_a_dependency_is_not_ready(client, harness):
    harness.probe.status = {"database": False}
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "dependencies": {"database": "not_ready"}}


@pytest.mark.anyio
async def test_health_endpoints_need_no_authentication(client):
    assert (await client.get("/health/live")).status_code == 200
    assert (await client.get("/health/ready")).status_code == 200
