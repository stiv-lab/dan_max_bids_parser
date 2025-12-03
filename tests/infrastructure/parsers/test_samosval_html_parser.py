# path: tests/infrastructure/parsers/test_samosval_html_parser.py
from __future__ import annotations

from dan_max_bids_parser.infrastructure.http.html_client import HtmlPage
from dan_max_bids_parser.infrastructure.parsers.samosval_html_parser import (
    SamosvalListingRaw,
    parse_samosval_list_page,
)


def test_parse_samosval_list_page_basic():
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

        <div class="order-card" data-id="102">
          <a class="order-card__link" href="/order/102">
            Вывоз грунта
          </a>
          <div class="order-card__route">
            <span class="from">СПб</span>
            <span class="to">ЛО, Всеволожск</span>
          </div>
          <div class="order-card__meta">
            <span class="weight">10 т</span>
            <span class="price">25 000 ₽</span>
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

    listings = parse_samosval_list_page(page)

    assert isinstance(listings, list)
    assert len(listings) == 2

    first = listings[0]
    assert isinstance(first, SamosvalListingRaw)
    assert first.external_id == "101"
    assert first.title == "Перевозка песка"
    assert first.route_from == "Москва"
    assert first.route_to == "МО, Балашиха"
    assert first.weight == "20 т"
    assert first.price == "35 000 ₽"
    assert first.meta_raw == "сегодня, щебень"
    assert first.url == "https://samosval.info/order/101"

    second = listings[1]
    assert second.external_id == "102"
    assert second.title == "Вывоз грунта"
    assert second.route_from == "СПб"
    assert second.route_to == "ЛО, Всеволожск"
    assert second.weight == "10 т"
    assert second.price == "25 000 ₽"
    # meta_raw не задано
    assert second.meta_raw is None
    assert second.url == "https://samosval.info/order/102"


def test_parse_samosval_list_page_skips_cards_without_link():
    html = """
    <html>
      <body>
        <div class="order-card" data-id="201">
          <!-- нет ссылки, карточка должна быть пропущена -->
          <div class="order-card__route">
            <span class="from">Москва</span>
            <span class="to">МО</span>
          </div>
        </div>
        <div class="order-card" data-id="202">
          <a class="order-card__link" href="/order/202">Корректная заявка</a>
        </div>
      </body>
    </html>
    """

    page = HtmlPage(
        url="https://samosval.info/orders",
        content=html,
        encoding="utf-8",
    )

    listings = parse_samosval_list_page(page)

    # Должна остаться только одна валидная карточка
    assert len(listings) == 1
    assert listings[0].external_id == "202"
    assert listings[0].title == "Корректная заявка"
