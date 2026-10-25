from dataclasses import dataclass


@dataclass(frozen=True)
class Migration:
    version: str
    sql: str
    checksum: str
