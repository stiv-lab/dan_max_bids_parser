# path: tests/infrastructure/providers/test_samosval_raw_item_provider.py
from __future__ import annotations

from typing import Any, Dict, Optional

from dan_max_bids_parser.infrastructure.http.html_client import HtmlPage
from dan_max_bids_parser.infrastructure.parsers.samosval_html_parser import (
    SamosvalListingRaw,
)
from dan_max_bids_parser.infrastructure.providers.samosval_raw_item_provider import (
    SamosvalRawItemProvider,
)


class DummyHtmlClient:
    """Поддельный HtmlClientProtocol для тестов.

    Возвращает заранее подготовленный HtmlPage и запоминает параметры вызова.
    """

    def __init__(self, page: HtmlPage) -> None:
        self._page = page
        self.last_request: Dict[str, Any] = {}

    def get(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HtmlPage:
        self.last_request = {
            "url": url,
            "params": params,
            "headers": headers,
            "timeout": timeout,
        }
        return self._page


def test_samosval_raw_item_provider_fetch_listings_basic():
    html = """
    <html>
      <body>
        <div class="order-card" data-id="101">
          <a class="order-card__link" href="/order/101">
            Перевозка песка
          </a>
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
      </body>
    </html>
    """

    page = HtmlPage(
        url="https://samosval.info/orders",
        content=html,
        encoding="utf-8",
    )
    client = DummyHtmlClient(page)
    provider = SamosvalRawItemProvider(
        html_client=client,
        listings_url="https://samosval.info/orders",
    )

    listings = provider.fetch_listings()

    # Проверяем, что был вызван правильный URL
    assert client.last_request["url"] == "https://samosval.info/orders"

    # Проверяем базовую корректность результата
    assert isinstance(listings, list)
    assert len(listings) == 1

    listing = listings[0]
    assert isinstance(listing, SamosvalListingRaw)
    assert listing.external_id == "101"
    assert listing.title == "Перевозка песка"
    assert listing.route_from == "Москва"
    assert listing.route_to == "МО, Балашиха"
    assert listing.weight == "20 т"
    assert listing.price == "35 000 ₽"
    assert listing.meta_raw == "сегодня, щебень"
    assert listing.url == "https://samosval.info/order/101"
