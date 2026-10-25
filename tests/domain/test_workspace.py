import hashlib
from datetime import UTC, datetime, timedelta, timezone

import pytest

from rag_lab.domain.shared.exceptions.invalid_session_token_hash import InvalidSessionTokenHash
from rag_lab.domain.shared.exceptions.invalid_workspace_id import InvalidWorkspaceId
from rag_lab.domain.shared.value_objects.session_token_hash import SessionTokenHash
from rag_lab.domain.shared.value_objects.workspace_id import WorkspaceId
from rag_lab.domain.workspaces.entities.workspace import Workspace
from rag_lab.domain.workspaces.exceptions.invalid_workspace import InvalidWorkspace

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
WORKSPACE_ID = WorkspaceId("00000000-0000-4000-8000-000000000001")
LIFETIME = timedelta(hours=24)


def workspace() -> Workspace:
    return Workspace.create(WORKSPACE_ID, SessionTokenHash.of("token"), NOW, LIFETIME)


def test_expiry_is_creation_plus_lifetime():
    assert workspace().expires_at == NOW + LIFETIME


def test_not_expired_before_the_expiry_instant():
    assert not workspace().is_expired(NOW + LIFETIME - timedelta(microseconds=1))


def test_expired_when_now_equals_expiry():
    assert workspace().is_expired(NOW + LIFETIME)


def test_expired_after_the_expiry_instant():
    assert workspace().is_expired(NOW + LIFETIME + timedelta(seconds=1))


def test_expiry_compares_instants_across_timezones():
    other_zone = timezone(timedelta(hours=-3))
    assert workspace().is_expired((NOW + LIFETIME).astimezone(other_zone))


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(hours=-1)])
def test_non_positive_lifetime_is_rejected(lifetime):
    with pytest.raises(InvalidWorkspace):
        Workspace.create(WORKSPACE_ID, SessionTokenHash.of("token"), NOW, lifetime)


def test_naive_timestamps_are_rejected():
    with pytest.raises(InvalidWorkspace):
        Workspace(WORKSPACE_ID, SessionTokenHash.of("t"), datetime(2026, 1, 1), NOW)


def test_expiry_must_follow_creation():
    with pytest.raises(InvalidWorkspace):
        Workspace(WORKSPACE_ID, SessionTokenHash.of("t"), NOW, NOW)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not-a-uuid",
        "00000000-0000-4000-8000-00000000000",
        "00000000000040008000000000000001",
        "{00000000-0000-4000-8000-000000000001}",
        "00000000-0000-4000-8000-00000000000G",
        "ABCDEF00-0000-4000-8000-000000000001",
        None,
        42,
    ],
)
def test_invalid_workspace_identifiers_are_rejected(value):
    with pytest.raises(InvalidWorkspaceId):
        WorkspaceId(value)


def test_valid_workspace_identifier_is_kept():
    assert str(WORKSPACE_ID) == "00000000-0000-4000-8000-000000000001"


@pytest.mark.parametrize(
    "value",
    ["", "abc", "g" * 64, "A" * 64, "a" * 63, "a" * 65, " " + "a" * 63, None],
)
def test_invalid_token_hashes_are_rejected(value):
    with pytest.raises(InvalidSessionTokenHash):
        SessionTokenHash(value)


def test_hash_is_the_sha256_of_the_token():
    assert SessionTokenHash.of("token").value == hashlib.sha256(b"token").hexdigest()


def test_empty_token_cannot_be_hashed():
    with pytest.raises(InvalidSessionTokenHash):
        SessionTokenHash.of("")


def test_hash_representation_hides_the_digest():
    token_hash = SessionTokenHash.of("token")
    assert token_hash.value not in repr(token_hash)
