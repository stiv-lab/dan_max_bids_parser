# path: tests/domain/test_entities_basic.py
from datetime import datetime

from dan_max_bids_parser.domain.entities import (
    BidEntity,
    RawItemEntity,
    SourceEntity,
)


def test_source_entity_creation():
    source = SourceEntity(
        id=None,
        code="ATI",
        name="ATI.su",
        kind="html",
        is_active=True,
        description="Транспортная биржа ATI",
    )

    assert source.code == "ATI"
    assert source.is_active is True
    assert "ATI" in source.name


def test_raw_item_entity_creation():
    now = datetime.utcnow()
    raw_item = RawItemEntity(
        id=None,
        source_id=1,
        external_id="123",
        payload="<html>...</html>",
        url="https://example.com/item/123",
        created_at=now,
        received_at=now,
    )

    assert raw_item.source_id == 1
    assert "html" in raw_item.payload
    assert raw_item.url.endswith("123")


def test_bid_entity_creation():
    bid = BidEntity(
        id=None,
        source_id=1,
        raw_item_id=10,
        external_id="BID-1",
        title="Перевозка песка",
        description="Нужна перевозка песка, 20 т.",
        cargo_type="песок",
        transport_type="самосвал",
        load_point="Москва",
        unload_point="Зеленоград",
        weight_tons=20.0,
        price=15000.0,
        currency="RUB",
        contact="+7 900 000-00-00",
        url="https://example.com/bid/1",
    )

    assert bid.source_id == 1
    assert bid.cargo_type == "песок"
    assert bid.weight_tons == 20.0
    assert "Перевозка" in bid.title
