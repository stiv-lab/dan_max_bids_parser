# path: src/dan_max_bids_parser/application/unit_of_work.py
from __future__ import annotations

from typing import Protocol, TypeVar

from dan_max_bids_parser.domain.ports import (
    BidRepositoryPort,
    RawItemRepositoryPort,
    SourceRepositoryPort,
)

TUnitOfWork = TypeVar("TUnitOfWork", bound="UnitOfWork")


class UnitOfWork(Protocol):
    """
    Абстракция UnitOfWork для координции работы с репозиториями и транзакциями.

    Чистый контракт, без привязки к конкретной ORM/БД.
    Инфраструктурная реализация будет, например, SqlAlchemyUnitOfWork.
    """

    sources: SourceRepositoryPort
    raw_items: RawItemRepositoryPort
    bids: BidRepositoryPort

    def commit(self) -> None:
        """Зафиксировать текущую транзакцию."""
        ...

    def rollback(self) -> None:
        """Откатить текущую транзакцию."""
        ...

    def __enter__(self: TUnitOfWork) -> TUnitOfWork:
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        ...
