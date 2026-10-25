from typing import Protocol

from rag_lab.application.ports.unit_of_work import UnitOfWork


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
