import hashlib

import pytest

from rag_lab.infrastructure.persistence.discover_migrations import (
    MIGRATIONS_DIRECTORY,
    discover_migrations,
)


def test_shipped_migrations_are_numbered_without_gaps_and_start_with_the_ledger():
    migrations = discover_migrations()
    numbers = [int(migration.version[:4]) for migration in migrations]
    assert numbers == list(range(1, len(numbers) + 1))
    assert migrations[0].version == "0001_schema_migrations"
    assert "schema_migrations" in migrations[0].sql


def test_migrations_are_returned_in_order(tmp_path):
    (tmp_path / "0002_second.sql").write_text("select 2;", encoding="utf-8")
    (tmp_path / "0001_first.sql").write_text("select 1;", encoding="utf-8")
    assert [m.version for m in discover_migrations(tmp_path)] == ["0001_first", "0002_second"]


def test_checksum_is_the_sha256_of_the_content(tmp_path):
    (tmp_path / "0001_first.sql").write_text("select 1;\n", encoding="utf-8")
    [migration] = discover_migrations(tmp_path)
    assert migration.checksum == hashlib.sha256(b"select 1;\n").hexdigest()


def test_checksum_changes_when_content_changes(tmp_path):
    path = tmp_path / "0001_first.sql"
    path.write_text("select 1;", encoding="utf-8")
    original = discover_migrations(tmp_path)[0].checksum
    path.write_text("select 2;", encoding="utf-8")
    assert discover_migrations(tmp_path)[0].checksum != original


def test_checksum_ignores_line_ending_style(tmp_path):
    path = tmp_path / "0001_first.sql"
    path.write_bytes(b"select 1;\nselect 2;\n")
    unix = discover_migrations(tmp_path)[0].checksum
    path.write_bytes(b"select 1;\r\nselect 2;\r\n")
    assert discover_migrations(tmp_path)[0].checksum == unix


@pytest.mark.parametrize("name", ["first.sql", "1_first.sql", "0001_First.sql", "0001 first.sql"])
def test_badly_named_migration_files_are_refused(tmp_path, name):
    (tmp_path / name).write_text("select 1;", encoding="utf-8")
    with pytest.raises(ValueError, match="Migration file name"):
        discover_migrations(tmp_path)


def test_migrations_directory_ships_with_the_package():
    assert MIGRATIONS_DIRECTORY.is_dir()
