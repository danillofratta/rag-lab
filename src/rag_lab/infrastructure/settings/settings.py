from datetime import timedelta
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration read from ``RAG_LAB_*`` variables (and an optional ``.env`` file).

    Secrets use ``SecretStr`` so they never render in logs, reprs or error messages.
    """

    model_config = SettingsConfigDict(
        env_prefix="RAG_LAB_",
        env_file=".env",
        extra="ignore",
        frozen=True,
    )

    database_url: SecretStr
    workspace_lifetime_hours: int = Field(default=24, gt=0, le=24 * 30)
    max_body_bytes: int = Field(default=1_048_576, gt=0, le=100 * 1024 * 1024)
    docs_enabled: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: SecretStr) -> SecretStr:
        # Messages never include the value: it contains the database password.
        try:
            parts = urlsplit(value.get_secret_value())
            port = parts.port
        except ValueError:
            raise ValueError("must be a postgresql:// URL") from None
        valid = (
            parts.scheme in {"postgresql", "postgres"}
            and bool(parts.hostname)
            and bool(parts.path.strip("/"))
            and (port is None or 0 < port < 65536)
        )
        if not valid:
            raise ValueError("must be a postgresql:// URL with host and database name")
        return value

    @property
    def workspace_lifetime(self) -> timedelta:
        return timedelta(hours=self.workspace_lifetime_hours)
