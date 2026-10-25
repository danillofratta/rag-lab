from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckHealthResult:
    ready: bool
    dependencies: Mapping[str, bool]
