# path: tests/infrastructure/providers/test_samosval_raw_item_provider_adapter.py

import json
from dataclasses import dataclass
from typing import List

from dan_max_bids_parser.domain.entities import RawItemEntity, SourceEntity
from dan_max_bids_parser.infrastructure.adapters.samosval_raw_item_provider_adapter import (
    SamosvalRawItemProviderAdapter,
)
from dan_max_bids_parser.infrastructure.parsers.samosval_html_parser import (
    SamosvalListingRaw,
)
from dan_max_bids_parser.infrastructure.providers.samosval_raw_item_provider import (
    SamosvalRawItemProvider,
)


@dataclass
class DummyProvider(SamosvalRawItemProvider):
    """Упрощённый провайдер, который не выполняет HTTP-запросов."""

    listings: List[SamosvalListingRaw]

    def fetch_listings(self):
        return list(self.listings)


def test_adapter_maps_listing_to_raw_item():
    listings = [
        SamosvalListingRaw(
            external_id="123",
            title="Перевозка песка",
            route_from="Москва",
            route_to="Балашиха",
            weight="20 т",
            price="35 000 ₽",
            meta_raw="сегодня, щебень",
            url="https://samosval.info/order/123",
        )
    ]

    provider = DummyProvider(listings=listings)
    adapter = SamosvalRawItemProviderAdapter(provider)
    source = SourceEntity(id=10, code="samosval", name="Samosval Info", kind="html")

    items = list(adapter.fetch_raw_items(source))
    assert len(items) == 1

    raw: RawItemEntity = items[0]
    assert raw.external_id == "123"
    assert raw.url == "https://samosval.info/order/123"

    payload = json.loads(raw.payload)
    assert payload["title"] == "Перевозка песка"
    assert payload["route_from"] == "Москва"
    assert payload["route_to"] == "Балашиха"
    assert payload["weight"] == "20 т"
    assert payload["price"] == "35 000 ₽"
    assert payload["meta_raw"] == "сегодня, щебень"
