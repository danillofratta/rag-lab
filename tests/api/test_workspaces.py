from datetime import datetime, timedelta

import pytest

from tests.api.conftest import LIFETIME_HOURS
from tests.fakes import START

LIFETIME = timedelta(hours=LIFETIME_HOURS)


def bearer(token):
    return {"authorization": f"Bearer {token}"}


async def create(client):
    response = await client.post("/workspaces")
    assert response.status_code == 201
    return response.json()


@pytest.mark.anyio
async def test_creation_returns_identifier_token_and_expiry_one_lifetime_later(client):
    body = await create(client)
    assert body["workspace_id"]
    assert len(body["session_token"]) >= 43
    assert datetime.fromisoformat(body["created_at"]) == START
    assert datetime.fromisoformat(body["expires_at"]) == START + LIFETIME


@pytest.mark.anyio
async def test_creation_accepts_an_empty_json_object(client):
    response = await client.post("/workspaces", json={})
    assert response.status_code == 201


@pytest.mark.anyio
async def test_creation_rejects_unknown_fields(client, harness):
    response = await client.post("/workspaces", json={"workspace_id": "x"})
    assert response.status_code == 422
    assert response.json() == {"error": "INVALID_INPUT"}
    assert harness.store.rows == {}


@pytest.mark.anyio
async def test_workspaces_have_distinct_identifiers_and_tokens(client):
    first, second = await create(client), await create(client)
    assert first["workspace_id"] != second["workspace_id"]
    assert first["session_token"] != second["session_token"]


@pytest.mark.anyio
async def test_current_workspace_is_read_with_the_session_token(client):
    body = await create(client)
    response = await client.get("/workspaces/current", headers=bearer(body["session_token"]))
    assert response.status_code == 200
    assert response.json()["workspace_id"] == body["workspace_id"]
    assert datetime.fromisoformat(response.json()["expires_at"]) == START + LIFETIME


@pytest.mark.anyio
async def test_each_token_sees_only_its_own_workspace(client):
    first, second = await create(client), await create(client)
    seen = await client.get("/workspaces/current", headers=bearer(second["session_token"]))
    assert seen.json()["workspace_id"] == second["workspace_id"] != first["workspace_id"]


UNKNOWN = "Z" * 43


@pytest.mark.anyio
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"authorization": "Bearer"},
        {"authorization": "Bearer short"},
        {"authorization": "Basic " + UNKNOWN},
        {"authorization": "Bearer " + "!" * 43},
        {"authorization": "Bearer " + UNKNOWN},
    ],
)
async def test_invalid_credentials_get_the_same_401_body(client, headers):
    await create(client)
    response = await client.get("/workspaces/current", headers=headers)
    assert response.status_code == 401
    assert response.json() == {"error": "UNAUTHENTICATED"}


@pytest.mark.anyio
async def test_missing_malformed_and_unknown_tokens_are_byte_identical(client):
    responses = [
        await client.get("/workspaces/current"),
        await client.get("/workspaces/current", headers=bearer("short")),
        await client.get("/workspaces/current", headers=bearer(UNKNOWN)),
    ]
    assert len({response.content for response in responses}) == 1
    assert len({response.status_code for response in responses}) == 1


@pytest.mark.anyio
async def test_session_expires_exactly_at_the_expiry_instant(client, harness):
    token = (await create(client))["session_token"]
    harness.clock.advance(LIFETIME - timedelta(microseconds=1))
    assert (await client.get("/workspaces/current", headers=bearer(token))).status_code == 200
    harness.clock.advance(timedelta(microseconds=1))
    response = await client.get("/workspaces/current", headers=bearer(token))
    assert response.status_code == 401
    assert response.json() == {"error": "SESSION_EXPIRED"}


@pytest.mark.anyio
async def test_activity_does_not_extend_expiry(client, harness):
    body = await create(client)
    for _ in range(3):
        harness.clock.advance(timedelta(hours=1))
        response = await client.get("/workspaces/current", headers=bearer(body["session_token"]))
        assert response.json()["expires_at"] == body["expires_at"]


@pytest.mark.anyio
async def test_inspection_changes_no_stored_state(client, harness):
    body = await create(client)
    rows, commits = dict(harness.store.rows), harness.store.commits
    for _ in range(3):
        await client.get("/workspaces/current", headers=bearer(body["session_token"]))
    assert harness.store.rows == rows
    assert harness.store.commits == commits


@pytest.mark.anyio
async def test_no_workspace_scoped_endpoint_accepts_a_workspace_identifier(docs_harness):
    schema = docs_harness.app.openapi()
    public = {("post", "/workspaces"), ("get", "/health/live"), ("get", "/health/ready")}
    scoped = [
        (method, path, operation)
        for path, methods in schema["paths"].items()
        for method, operation in methods.items()
        if (method, path) not in public
    ]
    assert scoped, "expected at least one workspace-scoped endpoint"
    for method, path, operation in scoped:
        assert "workspace" not in path.replace("/workspaces", ""), (method, path)
        for parameter in operation.get("parameters", []):
            assert "workspace" not in parameter["name"].lower(), (method, path)
        assert "requestBody" not in operation, (method, path)
