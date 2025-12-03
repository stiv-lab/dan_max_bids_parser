# path: src/dan_max_bids_parser/infrastructure/http/html_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol

import requests
from bs4 import BeautifulSoup, SoupStrainer


class HttpClientError(Exception):
    """Базовое исключение для ошибок HTTP-клиента."""


class HttpRequestError(HttpClientError):
    """Ошибка при выполнении HTTP-запроса."""


class HttpResponseError(HttpClientError):
    """HTTP-ответ с неожиданным статус-кодом."""


@dataclass
class HtmlPage:
    """Результат загрузки HTML-страницы.

    Attributes:
        url: Итоговый URL (с учётом редиректов).
        content: Текст HTML.
        encoding: Использованная кодировка (если известна).
    """

    url: str
    content: str
    encoding: Optional[str] = None


class HtmlClientProtocol(Protocol):
    """Протокол для HTML-клиента.

    Используется адаптерами источников для получения HTML-страниц.
    """

    def get(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HtmlPage:
        """Выполнить GET-запрос и вернуть HTML-страницу."""
        ...


class RequestsHtmlClient(HtmlClientProtocol):
    """Реализация HtmlClientProtocol на базе requests.Session.

    Поддерживает:
    - базовые заголовки (User-Agent, Accept-Language);
    - переопределение/дополнение заголовков на уровне вызова;
    - настройку таймаута по умолчанию.
    """

    def __init__(
        self,
            *,
            base_headers: Optional[Mapping[str, str]] = None,
            default_timeout: float = 10.0,
            session: Optional[requests.Session] = None,
        ) -> None:
        self._session = session or requests.Session()
        self._default_timeout = default_timeout

        default_headers: Dict[str, str] = {
            # Базовый User-Agent, чтобы не светиться как "python-requests/..."
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        if base_headers:
            default_headers.update(base_headers)

        self._base_headers = default_headers

    def get(
        self,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HtmlPage:
        """Выполнить GET-запрос и вернуть HtmlPage.

        При ошибках сети или статусах >= 400 кидает HttpClientError.
        """
        merged_headers = self._merge_headers(headers)

        try:
            response = self._session.get(
                url,
                params=params,
                headers=merged_headers,
                timeout=timeout or self._default_timeout,
            )
        except requests.RequestException as exc:
            raise HttpRequestError(f"HTTP request failed for {url!r}: {exc}") from exc

        if response.status_code >= 400:
            raise HttpResponseError(
                f"Unexpected status code {response.status_code} for {url!r}"
            )

        # Попытка корректно определить кодировку:
        # - если указана явно сервером — используем её;
        # - иначе оставляем autodetect от requests.
        encoding = response.encoding or response.apparent_encoding
        if encoding:
            response.encoding = encoding

        return HtmlPage(
            url=str(response.url),
            content=response.text,
            encoding=encoding,
        )

    def _merge_headers(
        self, extra: Optional[Mapping[str, str]]
    ) -> Dict[str, str]:
        """Объединить базовые заголовки с дополнительными.

        Дополнительные заголовки перекрывают базовые.
        """
        headers = dict(self._base_headers)
        if extra:
            headers.update(extra)
        return headers


def parse_html(
    html_page: HtmlPage,
    *,
    parser: str = "lxml",
    parse_only: Optional[SoupStrainer] = None,
) -> BeautifulSoup:
    """Построить BeautifulSoup-дом из HtmlPage.

    Args:
        html_page: Объект HtmlPage с текстом HTML.
        parser: Имя HTML-парсера для BeautifulSoup (`"lxml"` по умолчанию).
        parse_only: Опционально — SoupStrainer для частичного парсинга.

    Returns:
        Объект BeautifulSoup.
    """
    return BeautifulSoup(html_page.content, parser, parse_only=parse_only)
