# path: tests/application/test_unit_of_work_contract.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from dan_max_bids_parser.application.unit_of_work import UnitOfWork
from dan_max_bids_parser.domain.entities import BidEntity, RawItemEntity, SourceEntity
from dan_max_bids_parser.domain.ports import (
    BidRepositoryPort,
    RawItemRepositoryPort,
    SourceRepositoryPort,
)


# --- Простые fake-реализации портов для проверки интерфейса ---


@dataclass
class InMemorySourceRepository(SourceRepositoryPort):
    items: List[SourceEntity]

    def get_by_id(self, source_id: int) -> Optional[SourceEntity]:
        return next((s for s in self.items if s.id == source_id), None)

    def get_by_code(self, code: str) -> Optional[SourceEntity]:
        return next((s for s in self.items if s.code == code), None)

    def list_all(self):
        return list(self.items)

    def list_active(self):
        return [s for s in self.items if s.is_active]

    def save(self, source: SourceEntity) -> SourceEntity:
        if source.id is None:
            source.id = len(self.items) + 1
            self.items.append(source)
        else:
            for idx, existing in enumerate(self.items):
                if existing.id == source.id:
                    self.items[idx] = source
                    break
        return source


@dataclass
class InMemoryRawItemRepository(RawItemRepositoryPort):
    items: List[RawItemEntity]

    def add(self, raw_item: RawItemEntity) -> RawItemEntity:
        if raw_item.id is None:
            raw_item.id = len(self.items) + 1
        self.items.append(raw_item)
        return raw_item

    def add_many(self, raw_items):
        return [self.add(i) for i in raw_items]

    def get_by_id(self, raw_item_id: int) -> Optional[RawItemEntity]:
        return next((i for i in self.items if i.id == raw_item_id), None)

    def list_for_source_since(self, source_id, since):
        return [i for i in self.items if i.source_id == source_id]


@dataclass
class InMemoryBidRepository(BidRepositoryPort):
    items: List[BidEntity]

    def add(self, bid: BidEntity) -> BidEntity:
        if bid.id is None:
            bid.id = len(self.items) + 1
        self.items.append(bid)
        return bid

    def add_many(self, bids):
        return [self.add(b) for b in bids]

    def get_by_id(self, bid_id: int) -> Optional[BidEntity]:
        return next((b for b in self.items if b.id == bid_id), None)

    def list_for_source_since(self, source_id, since):
        return [b for b in self.items if b.source_id == source_id]

    def find_duplicates_candidates(self, bid: BidEntity):
        # для теста достаточно вернуть все заявки с тем же external_id
        return [b for b in self.items if b.external_id == bid.external_id]


class InMemoryUnitOfWork(UnitOfWork):
    """
    Простейшая реализация UnitOfWork в памяти,
    только для проверки, что контракт рабочий.
    """

    def __init__(self) -> None:
        self.sources = InMemorySourceRepository(items=[])
        self.raw_items = InMemoryRawItemRepository(items=[])
        self.bids = InMemoryBidRepository(items=[])
        self._committed = False

    def commit(self) -> None:
        self._committed = True

    def rollback(self) -> None:
        # в in-memory варианте просто сбрасываем флаг
        self._committed = False

    def __enter__(self) -> "InMemoryUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()


def test_unit_of_work_context_manager_and_repositories():
    uow = InMemoryUnitOfWork()

    with uow as tx:
        source = tx.sources.save(SourceEntity(code="ATI", name="ATI.su", kind="html"))
        bid = tx.bids.add(
            BidEntity(
                source_id=source.id or 0,
                title="Перевозка щебня",
                description="Нужна перевозка 30 т щебня",
            )
        )

        assert source.id is not None
        assert bid.id is not None

    # после выхода из контекстного менеджера commit должен быть вызван
    assert uow._committed is True
    assert len(uow.bids.items) == 1
