from rag_lab.application.ports.health_probe import HealthProbe
from rag_lab.features.check_health.query import CheckHealthQuery
from rag_lab.features.check_health.result import CheckHealthResult


class CheckHealthHandler:
    def __init__(self, probe: HealthProbe) -> None:
        self._probe = probe

    async def handle(self, query: CheckHealthQuery) -> CheckHealthResult:
        dependencies = dict(await self._probe.check())
        return CheckHealthResult(all(dependencies.values()), dependencies)
