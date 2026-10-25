import logging
import re

import pytest

from tests.api.conftest import BODY_LIMIT, Harness

REQUEST_ID = re.compile(r"[A-Za-z0-9-]{8,64}")
SECRET_BODY = "do-not-log-this-body-content"


def log_text(caplog):
    """Everything a log pipeline could emit: messages and every attribute of every record."""
    parts = []
    for record in caplog.records:
        parts.append(record.getMessage())
        parts.append(str(record.__dict__))
    return "\n".join(parts)


@pytest.mark.anyio
async def test_success_response_carries_a_request_id(client):
    response = await client.get("/health/live")
    assert REQUEST_ID.fullmatch(response.headers["x-request-id"])


@pytest.mark.anyio
async def test_failure_response_carries_a_request_id(client):
    response = await client.get("/no-such-route")
    assert response.status_code == 404
    assert response.json() == {"error": "NOT_FOUND"}
    assert REQUEST_ID.fullmatch(response.headers["x-request-id"])


@pytest.mark.anyio
async def test_each_request_gets_its_own_generated_id(client):
    first = await client.get("/health/live")
    second = await client.get("/health/live")
    assert first.headers["x-request-id"] != second.headers["x-request-id"]


@pytest.mark.anyio
async def test_well_formed_incoming_id_is_kept(client):
    response = await client.get("/health/live", headers={"x-request-id": "client-id-12345"})
    assert response.headers["x-request-id"] == "client-id-12345"


@pytest.mark.anyio
@pytest.mark.parametrize("incoming", ["short", "has spaces in it", "x" * 65, "bad;chars!!"])
async def test_malformed_incoming_id_is_replaced(client, incoming):
    response = await client.get("/health/live", headers={"x-request-id": incoming})
    assert response.headers["x-request-id"] != incoming
    assert REQUEST_ID.fullmatch(response.headers["x-request-id"])


@pytest.mark.anyio
async def test_the_same_id_appears_in_the_log_records(client, caplog):
    with caplog.at_level(logging.INFO, logger="rag_lab.access"):
        response = await client.get("/health/live")
    records = [r for r in caplog.records if r.name == "rag_lab.access"]
    assert records
    assert {r.request_id for r in records} == {response.headers["x-request-id"]}


@pytest.mark.anyio
async def test_declared_oversized_body_is_refused_without_invoking_the_handler(client, harness):
    response = await client.post("/workspaces", content=b"x" * (BODY_LIMIT + 1))
    assert response.status_code == 413
    assert response.json() == {"error": "BODY_TOO_LARGE"}
    assert response.headers["x-request-id"]
    assert harness.store.entered == 0


@pytest.mark.anyio
async def test_streamed_oversized_body_is_refused_without_invoking_the_handler(client, harness):
    async def chunks():
        yield b"x" * (BODY_LIMIT // 2 + 1)
        yield b"x" * (BODY_LIMIT // 2 + 1)

    response = await client.post("/workspaces", content=chunks())
    assert response.status_code == 413
    assert response.json() == {"error": "BODY_TOO_LARGE"}
    assert harness.store.entered == 0


@pytest.mark.anyio
async def test_body_exactly_at_the_limit_is_not_refused_for_size(client):
    response = await client.post("/workspaces", content=b"x" * BODY_LIMIT)
    assert response.status_code != 413


@pytest.mark.anyio
@pytest.mark.parametrize(
    "content",
    [b'{"unexpected": "do-not-echo-this-input"}', b"not json do-not-echo-this-input"],
)
async def test_invalid_input_is_422_without_echoing_it(client, content):
    response = await client.post(
        "/workspaces", content=content, headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json() == {"error": "INVALID_INPUT"}
    assert "do-not-echo-this-input" not in response.text


@pytest.mark.anyio
async def test_unexpected_failure_is_500_without_exception_text(harness: Harness, caplog):
    async def boom() -> None:
        raise RuntimeError("internal-detail-must-not-leak")

    harness.app.add_api_route("/boom", boom)
    with caplog.at_level(logging.DEBUG):
        async with harness.client() as client:
            response = await client.get("/boom")
    assert response.status_code == 500
    assert response.json() == {"error": "INTERNAL_ERROR"}
    assert response.headers["x-request-id"]
    assert "internal-detail-must-not-leak" not in response.text
    assert "internal-detail-must-not-leak" not in log_text(caplog)
    assert "Traceback" not in log_text(caplog)


@pytest.mark.anyio
async def test_authorization_headers_tokens_and_bodies_are_never_logged(client, caplog):
    created = await client.post("/workspaces")
    token = created.json()["session_token"]
    with caplog.at_level(logging.DEBUG):
        await client.get("/workspaces/current", headers={"authorization": f"Bearer {token}"})
        await client.get("/workspaces/current", headers={"authorization": "Bearer leaked-value-1"})
        await client.post(
            "/workspaces",
            content=f'{{"extra": "{SECRET_BODY}"}}'.encode(),
            headers={"content-type": "application/json", "authorization": "Bearer leaked-value-2"},
        )
    text = log_text(caplog)
    for secret in (token, "leaked-value-1", "leaked-value-2", SECRET_BODY):
        assert secret not in text
    assert any(record.name == "rag_lab.access" for record in caplog.records)
