from collections.abc import Mapping
from typing import Protocol


class HealthProbe(Protocol):
    async def check(self) -> Mapping[str, bool]:
        """Return readiness per dependency name. Never raises and never carries error details."""
        ...
