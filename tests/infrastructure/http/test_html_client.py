# path: tests/infrastructure/http/test_html_client.py
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest
import requests

from dan_max_bids_parser.infrastructure.http.html_client import (
    HtmlPage,
    HttpRequestError,
    HttpResponseError,
    RequestsHtmlClient,
)


class DummyResponse:
    """Поддельный объект ответа, имитирующий requests.Response."""

    def __init__(
        self,
        *,
        url: str = "https://example.com",
        status_code: int = 200,
        text: str = "<html><body>OK</body></html>",
        encoding: Optional[str] = "utf-8",
        apparent_encoding: Optional[str] = "utf-8",
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.text = text
        self.encoding = encoding
        self.apparent_encoding = apparent_encoding


class DummySession:
    """Поддельный Session, который возвращает заранее подготовленный ответ."""

    def __init__(self, response: DummyResponse | Exception) -> None:
        self._response_or_exc = response
        self.last_request: Dict[str, Any] = {}

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> DummyResponse:
        self.last_request = {
            "url": url,
            "params": params,
            "headers": headers,
            "timeout": timeout,
        }
        if isinstance(self._response_or_exc, Exception):
            raise self._response_or_exc
        return self._response_or_exc


def test_requests_html_client_success_basic():
    response = DummyResponse(
        url="https://example.com/page",
        status_code=200,
        text="<html><head><title>Test</title></head><body>Hello</body></html>",
        encoding="utf-8",
    )
    session = DummySession(response)
    client = RequestsHtmlClient(session=session)

    page = client.get("https://example.com/page")

    assert isinstance(page, HtmlPage)
    assert page.url == "https://example.com/page"
    assert "Hello" in page.content
    assert page.encoding == "utf-8"

    # Проверяем, что клиент передал URL и таймаут
    assert session.last_request["url"] == "https://example.com/page"
    assert session.last_request["timeout"] is not None


def test_requests_html_client_merges_headers():
    response = DummyResponse()
    session = DummySession(response)
    client = RequestsHtmlClient(
        session=session,
        base_headers={"User-Agent": "BaseUA", "X-Base": "1"},
    )

    page = client.get(
        "https://example.com",
        headers={"X-Extra": "2", "User-Agent": "OverrideUA"},
    )

    assert isinstance(page, HtmlPage)
    sent_headers = session.last_request["headers"]
    assert sent_headers["X-Base"] == "1"
    assert sent_headers["X-Extra"] == "2"
    # Дополнительный User-Agent должен перекрыть базовый
    assert sent_headers["User-Agent"] == "OverrideUA"


def test_requests_html_client_raises_on_request_error():
    session = DummySession(
        requests.RequestException("network error")
    )
    client = RequestsHtmlClient(session=session)

    with pytest.raises(HttpRequestError):
        client.get("https://example.com")


def test_requests_html_client_raises_on_bad_status_code():
    response = DummyResponse(status_code=500)
    session = DummySession(response)
    client = RequestsHtmlClient(session=session)

    with pytest.raises(HttpResponseError):
        client.get("https://example.com")
