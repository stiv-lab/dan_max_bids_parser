# path: src/dan_max_bids_parser/infrastructure/parsers/samosval_html_parser.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from dan_max_bids_parser.infrastructure.http.html_client import (
    HtmlPage,
    parse_html,
)


@dataclass
class SamosvalListingRaw:
    """Сырой объект заявки, извлечённый со страницы samosval.info.

    На этом уровне мы храним всё как строки, без строгой нормализации.
    Нормализация/классификация/маппинг в доменную BidEntity — отдельный слой.

    Attributes:
        external_id: Внешний идентификатор заявки (если удалось извлечь).
        title: Краткое описание заявки.
        route_from: Точка погрузки (как строка).
        route_to: Точка выгрузки (как строка).
        weight: Вес/объём груза (как строка, например "20 т").
        price: Цена (как строка, например "35 000 ₽").
        meta_raw: Дополнительные сырые метаданные (дата, тип груза и т.п.).
        url: Полный URL карточки заявки.
    """

    external_id: Optional[str]
    title: str
    route_from: Optional[str]
    route_to: Optional[str]
    weight: Optional[str]
    price: Optional[str]
    meta_raw: Optional[str]
    url: str


def parse_samosval_list_page(
    page: HtmlPage,
    *,
    base_url: Optional[str] = None,
):  # -> List[SamosvalListingRaw]:
    """Распарсить страницу списка заявок samosval.info в набор SamosvalListingRaw.

    ВАЖНО: селекторы ориентировочные. При интеграции с реальным HTML
    их нужно будет скорректировать под фактическую верстку сайта.

    Предполагаем структуру вида:

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

    Args:
        page: HtmlPage с контентом списка заявок.
        base_url: Базовый URL для построения абсолютных ссылок.
            Если не указан, используется page.url.

    Returns:
        Список SamosvalListingRaw.
    """
    soup = parse_html(page)
    container_selector = "div.order-card"
    cards: Iterable = soup.select(container_selector)

    result: List[SamosvalListingRaw] = []
    base = base_url or page.url

    for card in cards:
        # Внешний ID — из data-атрибута или части href.
        external_id = card.get("data-id")

        # Ссылка и заголовок
        link = card.select_one("a.order-card__link")
        if link is None:
            # Если структура другая, просто пропускаем такую карточку.
            continue

        href = link.get("href") or ""
        full_url = urljoin(base, href)
        title = (link.get_text() or "").strip()

        # Маршрут
        route_block = card.select_one(".order-card__route")
        if route_block is not None:
            route_from_el = route_block.select_one(".from")
            route_to_el = route_block.select_one(".to")
            route_from = route_from_el.get_text(strip=True) if route_from_el else None
            route_to = route_to_el.get_text(strip=True) if route_to_el else None
        else:
            route_from = None
            route_to = None

        # Метаданные: вес, цена, прочее
        meta_block = card.select_one(".order-card__meta")

        def _safe_text(sel: str) -> Optional[str]:
            if meta_block is None:
                return None
            el = meta_block.select_one(sel)
            return el.get_text(strip=True) if el else None

        weight = _safe_text(".weight")
        price = _safe_text(".price")

        extra_el = None
        if meta_block is not None:
            # всё, что не вес/цена, складываем в meta_raw
            # (например, дата, тип груза и т.п.)
            extra_el = meta_block.select_one(".extra")

        meta_raw = extra_el.get_text(strip=True) if extra_el else None

        result.append(
            SamosvalListingRaw(
                external_id=external_id,
                title=title,
                route_from=route_from,
                route_to=route_to,
                weight=weight,
                price=price,
                meta_raw=meta_raw,
                url=full_url,
            )
        )

    return result
