# path: src/dan_max_bids_parser/infrastructure/db/repositories.py
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from dan_max_bids_parser.domain.entities import BidEntity, RawItemEntity, SourceEntity
from dan_max_bids_parser.domain.ports import (
    BidRepositoryPort,
    RawItemRepositoryPort,
    SourceRepositoryPort,
)
from .models import Bid, RawItem, Source


# --- Вспомогательные функции маппинга ORM <-> Domain ---


def _source_to_entity(model: Source) -> SourceEntity:
    return SourceEntity(
        id=model.id,
        code=model.code,
        name=model.name,
        kind=model.kind,
        is_active=model.is_active,
        description=model.description or "",
    )


def _source_update_model_from_entity(model: Source, entity: SourceEntity) -> None:
    model.code = entity.code
    model.name = entity.name
    model.kind = entity.kind
    model.is_active = entity.is_active
    model.description = entity.description


# path: src/dan_max_bids_parser/infrastructure/db/repositories.py

def _raw_item_to_entity(model: RawItem) -> RawItemEntity:
    return RawItemEntity(
        id=model.id,
        source_id=model.source_id,
        external_id=model.external_id,
        payload=model.payload,
        url=model.url,
        # created_at — когда запись появилась в системе (из БД)
        created_at=model.created_at,
        # received_at — когда фактически забрали с источника (используем fetched_at)
        received_at=model.fetched_at,
    )


def _raw_item_update_model_from_entity(model: RawItem, entity: RawItemEntity) -> None:
    model.source_id = entity.source_id
    model.external_id = entity.external_id
    model.payload = entity.payload
    model.url = entity.url

    # fetched_at — момент получения данных с источника
    model.fetched_at = entity.received_at

    # created_at — когда мы зафиксировали raw-объект у себя
    model.created_at = entity.created_at



# path: src/dan_max_bids_parser/infrastructure/db/repositories.py

def _bid_to_entity(model: Bid) -> BidEntity:
    """
    ORM Bid -> доменная BidEntity.

    Маппим поля с учётом фактической схемы ORM-модели:
    - weight_value   -> weight_tons
    - price_value    -> price
    - load_location  -> load_point
    - unload_location-> unload_point
    - contact_phone  -> contact
    """
    return BidEntity(
        id=model.id,
        source_id=model.source_id,
        raw_item_id=model.raw_item_id,
        external_id=model.external_id,
        title=model.title,
        description=model.description or "",
        cargo_type=model.cargo_type,
        transport_type=model.transport_type,
        load_point=model.load_location,
        unload_point=model.unload_location,
        weight_tons=float(model.weight_value) if model.weight_value is not None else None,
        price=float(model.price_value) if model.price_value is not None else None,
        currency=model.price_currency,
        contact=model.contact_phone,
        url=model.url,
        published_at=model.published_at,
        created_at=model.created_at,
    )


def _bid_update_model_from_entity(model: Bid, entity: BidEntity) -> None:
    """
    Доменная BidEntity -> ORM Bid.

    Заполняем только те поля, которые реально существуют в модели Bid.
    Остальные (region, dedup_key и т.п.) оставляем на будущее.
    """
    model.source_id = entity.source_id
    model.raw_item_id = entity.raw_item_id
    model.external_id = entity.external_id
    model.title = entity.title
    model.description = entity.description
    model.cargo_type = entity.cargo_type
    model.transport_type = entity.transport_type

    # Маршрут
    model.load_location = entity.load_point
    model.unload_location = entity.unload_point

    # Вес / цена
    model.weight_value = entity.weight_tons
    model.weight_unit = "t" if entity.weight_tons is not None else None
    model.price_value = entity.price
    model.price_currency = entity.currency

    # Контакт и URL
    model.contact_phone = entity.contact
    model.url = entity.url

    # Временные метки
    model.published_at = entity.published_at
    model.received_at = getattr(entity, "received_at", None)  # на будущее, если появится

    # created_at — из доменной сущности
    model.created_at = entity.created_at

    # updated_at в схеме NOT NULL → по умолчанию считаем = created_at,
    # пока нет отдельной логики обновления.
    if getattr(model, "updated_at", None) is None:
        model.updated_at = entity.created_at



# --- Реализации портов ---


class SqlAlchemySourceRepository(SourceRepositoryPort):
    """
    Реализация SourceRepositoryPort через SQLAlchemy Session.

    Сессия передаётся извне (например, из UnitOfWork).
    Репозиторий не коммитит транзакции сам по себе.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, source_id: int) -> Optional[SourceEntity]:
        model = self._session.get(Source, source_id)
        if model is None:
            return None
        return _source_to_entity(model)

    def get_by_code(self, code: str) -> Optional[SourceEntity]:
        stmt = select(Source).where(Source.code == code)
        model = self._session.execute(stmt).scalar_one_or_none()
        if model is None:
            return None
        return _source_to_entity(model)

    def list_all(self) -> Sequence[SourceEntity]:
        stmt = select(Source).order_by(Source.id)
        result = self._session.execute(stmt).scalars().all()
        return [_source_to_entity(m) for m in result]

    def list_active(self) -> Sequence[SourceEntity]:
        stmt = select(Source).where(Source.is_active.is_(True)).order_by(Source.id)
        result = self._session.execute(stmt).scalars().all()
        return [_source_to_entity(m) for m in result]

    def save(self, source: SourceEntity) -> SourceEntity:
        if source.id is None:
            model = Source()
            _source_update_model_from_entity(model, source)
            self._session.add(model)
            self._session.flush()
            source.id = model.id
        else:
            model = self._session.get(Source, source.id)
            if model is None:
                model = Source(id=source.id)
                self._session.add(model)
            _source_update_model_from_entity(model, source)
            self._session.flush()
        return source


class SqlAlchemyRawItemRepository(RawItemRepositoryPort):
    """
    Реализация RawItemRepositoryPort через SQLAlchemy Session.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, raw_item: RawItemEntity) -> RawItemEntity:
        model = RawItem()
        _raw_item_update_model_from_entity(model, raw_item)
        self._session.add(model)
        self._session.flush()
        raw_item.id = model.id
        return raw_item

    def add_many(
        self, raw_items: Iterable[RawItemEntity]
    ) -> Sequence[RawItemEntity]:
        result = []
        for item in raw_items:
            result.append(self.add(item))
        return result

    def get_by_id(self, raw_item_id: int) -> Optional[RawItemEntity]:
        model = self._session.get(RawItem, raw_item_id)
        if model is None:
            return None
        return _raw_item_to_entity(model)

    def list_for_source_since(
        self,
        source_id: int,
        since: datetime,
    ) -> Sequence[RawItemEntity]:
        stmt = (
            select(RawItem)
            .where(
                RawItem.source_id == source_id,
                RawItem.created_at >= since,
            )
            .order_by(RawItem.created_at)
        )
        result = self._session.execute(stmt).scalars().all()
        return [_raw_item_to_entity(m) for m in result]


class SqlAlchemyBidRepository(BidRepositoryPort):
    """
    Реализация BidRepositoryPort через SQLAlchemy Session.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, bid: BidEntity) -> BidEntity:
        model = Bid()
        _bid_update_model_from_entity(model, bid)
        self._session.add(model)
        self._session.flush()
        bid.id = model.id
        return bid

    def add_many(self, bids: Iterable[BidEntity]) -> Sequence[BidEntity]:
        result = []
        for item in bids:
            result.append(self.add(item))
        return result

    def get_by_id(self, bid_id: int) -> Optional[BidEntity]:
        model = self._session.get(Bid, bid_id)
        if model is None:
            return None
        return _bid_to_entity(model)

    def list_for_source_since(
        self,
        source_id: int,
        since: datetime,
    ) -> Sequence[BidEntity]:
        stmt = (
            select(Bid)
            .where(
                Bid.source_id == source_id,
                Bid.created_at >= since,
            )
            .order_by(Bid.created_at)
        )
        result = self._session.execute(stmt).scalars().all()
        return [_bid_to_entity(m) for m in result]

    def find_duplicates_candidates(self, bid: BidEntity) -> Sequence[BidEntity]:
        """
        Базовая реализация: ищем заявки с тем же source_id и external_id.

        При необходимости в будущем можно заменить на более сложную стратегию
        (схожесть текста, маршрута, цены и т.п.).
        """
        stmt = select(Bid).where(
            Bid.source_id == bid.source_id,
            Bid.external_id == bid.external_id,
        )
        result = self._session.execute(stmt).scalars().all()
        return [_bid_to_entity(m) for m in result]
