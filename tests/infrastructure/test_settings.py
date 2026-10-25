from datetime import timedelta

import pytest

from rag_lab.infrastructure.settings.load_settings import load_settings

SECRET = "s3cr3t-pa55word"
VALID_URL = f"postgresql://rag_lab:{SECRET}@127.0.0.1:5432/rag_lab"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    # Settings must come only from what each test sets, never from the developer's shell.
    import os

    for name in list(os.environ):
        if name.startswith("RAG_LAB_"):
            monkeypatch.delenv(name)


def load():
    return load_settings(env_file=None)


def exit_message(monkeypatch, **variables):
    for name, value in variables.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(SystemExit) as exit_info:
        load()
    return str(exit_info.value)


def test_valid_settings_use_defaults(monkeypatch):
    monkeypatch.setenv("RAG_LAB_DATABASE_URL", VALID_URL)
    settings = load()
    assert settings.workspace_lifetime == timedelta(hours=24)
    assert settings.max_body_bytes == 1_048_576
    assert settings.docs_enabled is False


def test_values_are_read_from_the_prefixed_environment(monkeypatch):
    monkeypatch.setenv("RAG_LAB_DATABASE_URL", VALID_URL)
    monkeypatch.setenv("RAG_LAB_WORKSPACE_LIFETIME_HOURS", "2")
    monkeypatch.setenv("RAG_LAB_DOCS_ENABLED", "true")
    settings = load()
    assert settings.workspace_lifetime == timedelta(hours=2)
    assert settings.docs_enabled is True


def test_missing_database_url_names_the_setting(monkeypatch):
    message = exit_message(monkeypatch)
    assert "RAG_LAB_DATABASE_URL" in message


@pytest.mark.parametrize(
    "url",
    [
        f"mysql://u:{SECRET}@host/db",
        f"postgresql://u:{SECRET}@/db",
        f"postgresql://u:{SECRET}@host",
        f"postgresql://u:{SECRET}@host:notaport/db",
        f"postgresql://u:{SECRET}@host:99999/db",
        f"not a url {SECRET}",
    ],
)
def test_malformed_database_url_names_the_setting_and_hides_the_value(monkeypatch, url):
    message = exit_message(monkeypatch, RAG_LAB_DATABASE_URL=url)
    assert "RAG_LAB_DATABASE_URL" in message
    assert SECRET not in message


@pytest.mark.parametrize("hours", ["0", "-1", "abc", "", "100000"])
def test_out_of_range_workspace_lifetime_names_the_setting(monkeypatch, hours):
    message = exit_message(
        monkeypatch, RAG_LAB_DATABASE_URL=VALID_URL, RAG_LAB_WORKSPACE_LIFETIME_HOURS=hours
    )
    assert "RAG_LAB_WORKSPACE_LIFETIME_HOURS" in message
    assert SECRET not in message


@pytest.mark.parametrize("limit", ["0", "-5", "many"])
def test_invalid_body_limit_names_the_setting(monkeypatch, limit):
    message = exit_message(
        monkeypatch, RAG_LAB_DATABASE_URL=VALID_URL, RAG_LAB_MAX_BODY_BYTES=limit
    )
    assert "RAG_LAB_MAX_BODY_BYTES" in message


def test_every_invalid_setting_is_named_at_once(monkeypatch):
    message = exit_message(
        monkeypatch,
        RAG_LAB_WORKSPACE_LIFETIME_HOURS="0",
        RAG_LAB_MAX_BODY_BYTES="0",
    )
    for name in (
        "RAG_LAB_DATABASE_URL",
        "RAG_LAB_WORKSPACE_LIFETIME_HOURS",
        "RAG_LAB_MAX_BODY_BYTES",
    ):
        assert name in message


def test_secret_does_not_render_in_repr_or_str(monkeypatch):
    monkeypatch.setenv("RAG_LAB_DATABASE_URL", VALID_URL)
    settings = load()
    assert SECRET not in repr(settings)
    assert SECRET not in str(settings)
