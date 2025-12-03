# path: tests/application/test_run_source_harvesting_service.py
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Optional, Sequence

from dan_max_bids_parser.application.use_cases.harvest_source import (
    RunSourceHarvestingCommand,
)
from dan_max_bids_parser.application.use_cases.harvest_source_service import (
    RunSourceHarvestingService,
    UnitOfWorkFactory,
)
from dan_max_bids_parser.application.unit_of_work import UnitOfWork
from dan_max_bids_parser.domain.entities import BidEntity, RawItemEntity, SourceEntity
from dan_max_bids_parser.domain.ports import (
    BidRepositoryPort,
    RawItemRepositoryPort,
    SourceRepositoryPort,
)


# --- In-memory реализации портов для теста ---


class InMemorySourceRepository(SourceRepositoryPort):
    def __init__(self, sources: Iterable[SourceEntity]) -> None:
        self._by_id: dict[int, SourceEntity] = {}
        self._by_code: dict[str, SourceEntity] = {}
        for src in sources:
            if src.id is None:
                raise ValueError("InMemorySourceRepository требует source.id")
            self._by_id[src.id] = src
            self._by_code[src.code] = src

    def get_by_id(self, source_id: int) -> Optional[SourceEntity]:
        return self._by_id.get(source_id)

    def get_by_code(self, code: str) -> Optional[SourceEntity]:
        return self._by_code.get(code)

    def list_all(self) -> Sequence[SourceEntity]:
        return list(self._by_id.values())

    def list_active(self) -> Sequence[SourceEntity]:
        return [s for s in self._by_id.values() if s.is_active]

    def save(self, source: SourceEntity) -> SourceEntity:
        if source.id is None:
            raise ValueError("InMemorySourceRepository не создаёт новые id")
        self._by_id[source.id] = source
        self._by_code[source.code] = source
        return source


class InMemoryRawItemRepository(RawItemRepositoryPort):
    def __init__(self) -> None:
        self.items: list[RawItemEntity] = []
        self._next_id: int = 1

    def add(self, raw_item: RawItemEntity) -> RawItemEntity:
        if raw_item.id is None:
            raw_item.id = self._next_id
            self._next_id += 1
        self.items.append(raw_item)
        return raw_item

    def add_many(self, raw_items: Iterable[RawItemEntity]) -> Sequence[RawItemEntity]:
        result: list[RawItemEntity] = []
        for item in raw_items:
            result.append(self.add(item))
        return result

    def get_by_id(self, raw_item_id: int) -> Optional[RawItemEntity]:
        for item in self.items:
            if item.id == raw_item_id:
                return item
        return None

    def list_for_source_since(
        self,
        source_id: int,
        since,
    ) -> Sequence[RawItemEntity]:
        return [i for i in self.items if i.source_id == source_id and i.created_at >= since]


class InMemoryBidRepository(BidRepositoryPort):
    def __init__(self) -> None:
        self.items: list[BidEntity] = []
        self._next_id: int = 1

    def add(self, bid: BidEntity) -> BidEntity:
        if bid.id is None:
            bid.id = self._next_id
            self._next_id += 1
        self.items.append(bid)
        return bid

    def add_many(self, bids: Iterable[BidEntity]) -> Sequence[BidEntity]:
        result: list[BidEntity] = []
        for b in bids:
            result.append(self.add(b))
        return result

    def get_by_id(self, bid_id: int) -> Optional[BidEntity]:
        for item in self.items:
            if item.id == bid_id:
                return item
        return None

    def list_for_source_since(
        self,
        source_id: int,
        since,
    ) -> Sequence[BidEntity]:
        return [b for b in self.items if b.source_id == source_id and b.created_at >= since]

    def find_duplicates_candidates(self, bid: BidEntity) -> Sequence[BidEntity]:
        return [
            b
            for b in self.items
            if b.source_id == bid.source_id and b.external_id == bid.external_id
        ]


class InMemoryUnitOfWork(UnitOfWork):
    """
    Простая in-memory реализация UnitOfWork для теста use-case.

    Не использует реальную БД, но повторяет контракт:
    - репозитории,
    - commit / rollback,
    - контекстный менеджер.
    """

    def __init__(
        self,
        sources: InMemorySourceRepository,
        raw_items: InMemoryRawItemRepository,
        bids: InMemoryBidRepository,
    ) -> None:
        self.sources = sources
        self.raw_items = raw_items
        self.bids = bids
        self.committed: bool = False
        self.rolled_back: bool = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def __enter__(self) -> "InMemoryUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()


@dataclass
class StubRawItemProvider:
    """
    Заглушечный провайдер сырья: возвращает заранее заданный список RawItemEntity.
    """
    items: list[RawItemEntity]
    called_with: list[SourceEntity] = field(default_factory=list)

    def fetch_raw_items(self, source: SourceEntity) -> Iterable[RawItemEntity]:
        self.called_with.append(source)
        # возвращаем копии, чтобы не портить исходный список
        return list(self.items)


# --- Тесты ---


def test_run_source_harvesting_creates_raw_items_and_bids():
    # Arrange: источник + репозитории + UoW-фабрика + заглушка провайдера
    source = SourceEntity(
        id=1,
        code="ATI",
        name="ATI",
        kind="html",
        is_active=True,
        description="Test source",
    )

    source_repo = InMemorySourceRepository([source])
    raw_repo = InMemoryRawItemRepository()
    bid_repo = InMemoryBidRepository()

    provider_items = [
        RawItemEntity(source_id=source.id or 0, external_id="ext-1", payload="raw 1"),
        RawItemEntity(source_id=source.id or 0, external_id="ext-2", payload="raw 2"),
    ]
    raw_provider = StubRawItemProvider(items=provider_items)

    def uow_factory() -> UnitOfWork:
        return InMemoryUnitOfWork(source_repo, raw_repo, bid_repo)

    service = RunSourceHarvestingService(
        uow_factory=uow_factory,
        raw_item_provider=raw_provider,
    )

    cmd = RunSourceHarvestingCommand(source_code="ATI")

    # Act
    service.execute(cmd)

    # Assert: провайдер был вызван
    assert raw_provider.called_with == [source]

    # сырьё сохранено
    assert len(raw_repo.items) == 2
    assert {item.external_id for item in raw_repo.items} == {"ext-1", "ext-2"}

    # заявки созданы и связаны с raw_items и source
    assert len(bid_repo.items) == 2
    assert {bid.external_id for bid in bid_repo.items} == {"ext-1", "ext-2"}
    assert {bid.source_id for bid in bid_repo.items} == {source.id}
    assert all(bid.raw_item_id is not None for bid in bid_repo.items)


def test_run_source_harvesting_raises_if_source_not_found():
    # Arrange: пустой репозиторий источников
    source_repo = InMemorySourceRepository([])
    raw_repo = InMemoryRawItemRepository()
    bid_repo = InMemoryBidRepository()
    raw_provider = StubRawItemProvider(items=[])

    def uow_factory() -> UnitOfWork:
        return InMemoryUnitOfWork(source_repo, raw_repo, bid_repo)

    service = RunSourceHarvestingService(
        uow_factory=uow_factory,
        raw_item_provider=raw_provider,
    )

    cmd = RunSourceHarvestingCommand(source_code="UNKNOWN")

    # Act / Assert
    try:
        service.execute(cmd)
    except ValueError as exc:
        assert "Source with code='UNKNOWN' not found" in str(exc)
    else:
        assert False, "Ожидалось ValueError при отсутствии источника"
