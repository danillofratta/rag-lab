"""Sentinel scan: a generated token may appear only in its own creation response."""

import logging
from datetime import timedelta

import pytest


def bearer(token):
    return {"authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_tokens_appear_only_in_their_creation_response(client, harness, caplog):
    creations = [await client.post("/workspaces") for _ in range(3)]
    tokens = [response.json()["session_token"] for response in creations]
    assert len(set(tokens)) == 3

    observed = []
    with caplog.at_level(logging.DEBUG):
        for token in tokens:
            observed.append(await client.get("/workspaces/current", headers=bearer(token)))
            observed.append(await client.get("/workspaces/current", headers=bearer(token)))
        observed.append(await client.get("/workspaces/current"))
        observed.append(await client.get("/workspaces/current", headers=bearer("Z" * 43)))
        observed.append(await client.post("/workspaces", json={"nope": 1}))
        observed.append(await client.get("/health/ready"))
        observed.append(await client.get("/missing"))
        harness.clock.advance(timedelta(days=2))
        observed.append(await client.get("/workspaces/current", headers=bearer(tokens[0])))

    surfaces = {
        "responses": "\n".join(f"{r.headers}{r.text}" for r in observed),
        "logs": "\n".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records),
        "stored rows": repr(harness.store.rows),
    }
    for token in tokens:
        for name, text in surfaces.items():
            assert token not in text, f"token leaked into {name}"
    # The creation responses are the one place each token is allowed.
    for response, token in zip(creations, tokens, strict=True):
        assert token in response.text
        others = [other for other in tokens if other != token]
        assert not any(other in response.text for other in others)
