# path: src/dan_max_bids_parser/infrastructure/providers/samosval_raw_item_provider.py
from __future__ import annotations

from typing import List, Optional

from dan_max_bids_parser.infrastructure.http.html_client import (
    HtmlClientProtocol,
    HtmlPage,
)
from dan_max_bids_parser.infrastructure.parsers.samosval_html_parser import (
    SamosvalListingRaw,
    parse_samosval_list_page,
)


class SamosvalRawItemProvider:
    """Инфраструктурный провайдер HTML-страниц samosval.info.

    Задача этого класса — связать:
    - универсальный HtmlClient (HTTP-запрос),
    - парсер HTML-страницы списка заявок.

    На этом уровне мы работаем с сырыми структурами `SamosvalListingRaw`.
    Маппинг в доменные сущности (RawItemEntity / BidEntity) будет выполнен
    в другом слое (application/domain).
    """

    def __init__(
        self,
        html_client: HtmlClientProtocol,
        listings_url: str = "https://samosval.info/",
        *,
        base_url_override: Optional[str] = None,
    ) -> None:
        """Создать провайдер.

        Args:
            html_client: Реализация HtmlClientProtocol (обычно RequestsHtmlClient).
            listings_url: URL страницы со списком заявок. По умолчанию корень сайта.
            base_url_override: Опционально — базовый URL, который будет передан
                в парсер для построения абсолютных ссылок. Если не задан,
                используется фактический URL ответа (HtmlPage.url).
        """
        self._html_client = html_client
        self._listings_url = listings_url
        self._base_url_override = base_url_override

    def fetch_listings(self) -> List[SamosvalListingRaw]:
        """Загрузить HTML-страницу списка заявок и распарсить её.

        Returns:
            Список SamosvalListingRaw, полученных из HTML.
        """
        page: HtmlPage = self._html_client.get(self._listings_url)
        listings = parse_samosval_list_page(
            page,
            base_url=self._base_url_override,
        )
        return list(listings)
