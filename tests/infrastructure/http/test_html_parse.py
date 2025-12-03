# path: tests/infrastructure/http/test_html_parse.py
from __future__ import annotations

from bs4 import BeautifulSoup

from dan_max_bids_parser.infrastructure.http.html_client import (
    HtmlPage,
    parse_html,
)


def test_parse_html_builds_beautifulsoup():
    html = "<html><body><h1>Заголовок</h1></body></html>"
    page = HtmlPage(url="https://example.com", content=html, encoding="utf-8")

    soup = parse_html(page)

    assert isinstance(soup, BeautifulSoup)
    assert soup.h1 is not None
    assert soup.h1.text == "Заголовок"
