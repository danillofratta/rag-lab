from dataclasses import dataclass


@dataclass(frozen=True)
class CheckHealthQuery:
    """Ask whether every required dependency is reachable and the schema is current."""
