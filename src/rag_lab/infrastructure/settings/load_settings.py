from pydantic import ValidationError

from rag_lab.infrastructure.settings.settings import Settings

PREFIX = "RAG_LAB_"


def load_settings(env_file: str | None = ".env") -> Settings:
    """Load settings or exit naming every invalid variable, never its value."""
    try:
        return Settings(_env_file=env_file)
    except ValidationError as error:
        names = sorted({PREFIX + str(item["loc"][0]).upper() for item in error.errors()})
        raise SystemExit("Invalid configuration, check: " + ", ".join(names)) from None
