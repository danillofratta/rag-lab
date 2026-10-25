import hashlib
import re
from pathlib import Path

from rag_lab.infrastructure.persistence.migration import Migration

MIGRATIONS_DIRECTORY = Path(__file__).parent / "migrations"
_NAME = re.compile(r"\d{4}_[a-z0-9_]+\.sql")


def discover_migrations(directory: Path | None = None) -> list[Migration]:
    """Return the numbered SQL files in order. Checksums ignore line-ending differences."""
    folder = directory or MIGRATIONS_DIRECTORY
    migrations = []
    for path in sorted(folder.glob("*.sql")):
        if not _NAME.fullmatch(path.name):
            raise ValueError(f"Migration file name must look like 0001_name.sql: {path.name}")
        sql = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        migrations.append(Migration(path.stem, sql, checksum))
    return migrations
