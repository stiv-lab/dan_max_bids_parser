# path: tests/integration/test_samosval_harvesting_flow.py

"""
Интеграционный тест стека samosval.info:

HtmlClient -> SamosvalRawItemProvider -> SamosvalRawItemProviderAdapter
-> RunSourceHarvestingService -> UnitOfWork (in-memory).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from dan_max_bids_parser.application.use_cases.harvest_source import (
    RunSourceHarvestingCommand,
)
from dan_max_bids_parser.application.use_cases.harvest_source_service import (
    RunSourceHarvestingService,
)
from dan_max_bids_parser.domain.entities import BidEntity, RawItemEntity, SourceEntity
from dan_max_bids_parser.domain.ports import (
    BidRepositoryPort,
    RawItemRepositoryPort,
    SourceRepositoryPort,
)
from dan_max_bids_parser.infrastructure.adapters.samosval_raw_item_provider_adapter import (
    SamosvalRawItemProviderAdapter,
)
from dan_max_bids_parser.infrastructure.http.html_client import (
    HtmlClientProtocol,
    HtmlPage,
)
from dan_max_bids_parser.infrastructure.parsers.samosval_html_parser import (
    SamosvalListingRaw,
    parse_samosval_list_page,
)
from dan_max_bids_parser.infrastructure.providers.samosval_raw_item_provider import (
    SamosvalRawItemProvider,
)


# --- In-memory реализации репозиториев и UnitOfWork ---


class InMemorySourceRepository(SourceRepositoryPort):
    def __init__(self, sources: Iterable[SourceEntity]) -> None:
        self._sources = {s.code: s for s in sources}

    def get_by_id(self, source_id: int) -> Optional[SourceEntity]:
        for s in self._sources.values():
            if s.id == source_id:
                return s
        return None

    def get_by_code(self, code: str) -> Optional[SourceEntity]:
        return self._sources.get(code)

    def list_all(self) -> List[SourceEntity]:
        return list(self._sources.values())

    def list_active(self) -> List[SourceEntity]:
        return [s for s in self._sources.values() if s.is_active]

    def save(self, source: SourceEntity) -> SourceEntity:
        if source.id is None:
            source.id = max((s.id or 0 for s in self._sources.values()), default=0) + 1
        self._sources[source.code] = source
        return source


class InMemoryRawItemRepository(RawItemRepositoryPort):
    def __init__(self) -> None:
        self._items: List[RawItemEntity] = []
        self._next_id: int = 1

    def add(self, raw_item: RawItemEntity) -> RawItemEntity:
        if raw_item.id is None:
            raw_item.id = self._next_id
            self._next_id += 1
        self._items.append(raw_item)
        return raw_item

    def add_many(self, raw_items: Iterable[RawItemEntity]) -> List[RawItemEntity]:
        result: List[RawItemEntity] = []
        for item in raw_items:
            result.append(self.add(item))
        return result

    def get_by_id(self, raw_item_id: int) -> Optional[RawItemEntity]:
        for item in self._items:
            if item.id == raw_item_id:
                return item
        return None

    def list_for_source_since(self, source_id: int, since) -> List[RawItemEntity]:
        # Для целей теста фильтруем только по source_id.
        return [i for i in self._items if i.source_id == source_id]

    @property
    def items(self) -> List[RawItemEntity]:
        return list(self._items)


class InMemoryBidRepository(BidRepositoryPort):
    def __init__(self) -> None:
        self._bids: List[BidEntity] = []
        self._next_id: int = 1

    def add(self, bid: BidEntity) -> BidEntity:
        if bid.id is None:
            bid.id = self._next_id
            self._next_id += 1
        self._bids.append(bid)
        return bid

    def add_many(self, bids: Iterable[BidEntity]) -> List[BidEntity]:
        result: List[BidEntity] = []
        for b in bids:
            result.append(self.add(b))
        return result

    def get_by_id(self, bid_id: int) -> Optional[BidEntity]:
        for b in self._bids:
            if b.id == bid_id:
                return b
        return None

    def list_for_source_since(self, source_id: int, since) -> List[BidEntity]:
        return [b for b in self._bids if b.source_id == source_id]

    def find_duplicates_candidates(self, bid: BidEntity) -> List[BidEntity]:
        # Для теста можно вернуть пустой список.
        return []

    @property
    def bids(self) -> List[BidEntity]:
        return list(self._bids)


class InMemoryUnitOfWork:
    """
    Простая in-memory реализация UnitOfWork для интеграционного теста.

    Реализует только минимально необходимое поведение:
    - контекстный менеджер,
    - ссылки на репозитории,
    - commit/rollback как no-op.
    """

    def __init__(
        self,
        sources: SourceRepositoryPort,
        raw_items: InMemoryRawItemRepository,
        bids: InMemoryBidRepository,
    ) -> None:
        self.sources = sources
        self.raw_items = raw_items
        self.bids = bids

    def __enter__(self) -> "InMemoryUnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Для in-memory случая откат/commit ничего не делают.
        return None

    def commit(self) -> None:  # pragma: no cover - логика в памяти
        return None

    def rollback(self) -> None:  # pragma: no cover
        return None


# --- Фейки для HTML-клиента и провайдера ---


class FakeHtmlClient(HtmlClientProtocol):
    """
    HtmlClient, который возвращает заранее подготовленный HTML,
    чтобы не ходить в реальный интернет.
    """

    def __init__(self, html: str, url: str = "https://samosval.info/") -> None:
        self._html = html
        self._url = url

    def get(self, url: str, *, params=None, headers=None, timeout=None) -> HtmlPage:
        return HtmlPage(url=self._url, content=self._html, encoding="utf-8")


def _build_test_html() -> str:
    """
    Cинтетический HTML, совместимый с parse_samosval_list_page.
    """
    return """
    <html>
      <body>
        <div class="order-card" data-id="123">
          <a class="order-card__link" href="/order/123">Перевозка песка</a>
          <div class="order-card__route">
            <span class="from">Москва</span>
            <span class="to">МО, Балашиха</span>
          </div>
          <div class="order-card__meta">
            <span class="weight">20 т</span>
            <span class="price">35 000 ₽</span>
            <span class="extra">сегодня, щебень</span>
          </div>
        </div>
        <div class="order-card" data-id="124">
          <a class="order-card__link" href="/order/124">Вывоз грунта</a>
          <div class="order-card__route">
            <span class="from">СПб</span>
            <span class="to">ЛО, Всеволожск</span>
          </div>
          <div class="order-card__meta">
            <span class="weight">10 т</span>
            <span class="price">20 000 ₽</span>
            <span class="extra">вчера, грунт</span>
          </div>
        </div>
      </body>
    </html>
    """


def test_samosval_harvesting_end_to_end_inmemory():
    # 1. Источник
    source = SourceEntity(
        id=1,
        code="samosval",
        name="Samosval Info",
        kind="html",
        is_active=True,
    )

    # 2. In-memory репозитории и UoW-фабрика
    source_repo = InMemorySourceRepository([source])
    raw_repo = InMemoryRawItemRepository()
    bid_repo = InMemoryBidRepository()

    def uow_factory() -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork(
            sources=source_repo,
            raw_items=raw_repo,
            bids=bid_repo,
        )

    # 3. HTML-слой: FakeHtmlClient -> SamosvalRawItemProvider -> Adapter
    html_client = FakeHtmlClient(_build_test_html())
    samosval_provider = SamosvalRawItemProvider(
        html_client=html_client,
        listings_url="https://samosval.info/",
    )
    adapter = SamosvalRawItemProviderAdapter(samosval_provider)

    # 4. RunSourceHarvestingService
    service = RunSourceHarvestingService(
        uow_factory=uow_factory,
        raw_item_provider=adapter,
    )

    # 5. Запускаем use-case
    cmd = RunSourceHarvestingCommand(source_code="samosval")
    service.execute(cmd)

    # 6. Проверяем, что:
    #   - raw_items сохранены
    #   - bids созданы
    assert len(raw_repo.items) == 2
    assert len(bid_repo.bids) == 2

    # 7. Проверяем корректность маппинга payload и полей BidEntity
    first_raw = raw_repo.items[0]
    first_bid = bid_repo.bids[0]

    assert first_raw.source_id == source.id
    assert first_bid.source_id == source.id
    assert first_bid.raw_item_id == first_raw.id
    assert first_bid.url == first_raw.url

    payload = json.loads(first_raw.payload)
    assert payload["external_id"] == "123"
    assert payload["title"] == "Перевозка песка"
    assert payload["route_from"] == "Москва"
    assert payload["route_to"] == "МО, Балашиха"
    assert payload["weight"] == "20 т"
    assert payload["price"] == "35 000 ₽"
    assert payload["meta_raw"] == "сегодня, щебень"
