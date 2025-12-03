# path: src/dan_max_bids_parser/domain/ports.py
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, Optional, Protocol, Sequence

from .entities import BidEntity, RawItemEntity, SourceEntity


class SourceRepositoryPort(Protocol):
    """
    Порт доступа к источникам (SourceEntity).

    Реализации будут в infrastructure-слое (ORM/SQLAlchemy).
    """

    def get_by_id(self, source_id: int) -> Optional[SourceEntity]:
        ...

    def get_by_code(self, code: str) -> Optional[SourceEntity]:
        ...

    def list_all(self) -> Sequence[SourceEntity]:
        ...

    def list_active(self) -> Sequence[SourceEntity]:
        ...

    def save(self, source: SourceEntity) -> SourceEntity:
        ...


class RawItemRepositoryPort(Protocol):
    """
    Порт для работы с сырыми объектами (RawItemEntity).
    """

    def add(self, raw_item: RawItemEntity) -> RawItemEntity:
        ...

    def add_many(self, raw_items: Iterable[RawItemEntity]) -> Sequence[RawItemEntity]:
        ...

    def get_by_id(self, raw_item_id: int) -> Optional[RawItemEntity]:
        ...

    def list_for_source_since(
        self,
        source_id: int,
        since: datetime,
    ) -> Sequence[RawItemEntity]:
        ...


class BidRepositoryPort(Protocol):
    """
    Порт для работы с нормализованными заявками (BidEntity).
    """

    def add(self, bid: BidEntity) -> BidEntity:
        ...

    def add_many(self, bids: Iterable[BidEntity]) -> Sequence[BidEntity]:
        ...

    def get_by_id(self, bid_id: int) -> Optional[BidEntity]:
        ...

    def list_for_source_since(
        self,
        source_id: int,
        since: datetime,
    ) -> Sequence[BidEntity]:
        ...

    def find_duplicates_candidates(self, bid: BidEntity) -> Sequence[BidEntity]:
        """
        Возвращает кандидатов на дубликаты для заданной заявки.
        Конкретная стратегия будет определяться в реализации.
        """
        ...
