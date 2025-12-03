# path: src/dan_max_bids_parser/domain/entities.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class SourceEntity:
    """
    Доменная сущность источника заявок.

    Не зависит от ORM/БД. Используется в домене и application-слое.
    """
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    kind: str = ""  # html / telegram / api / whatsapp и т.п.
    is_active: bool = True
    description: str = ""


@dataclass(slots=True)
class RawItemEntity:
    """
    Сырой объект из источника:
    - HTML страницы,
    - JSON ответа API,
    - текст сообщения Telegram и т.п.
    """
    id: Optional[int] = None
    source_id: int = 0
    external_id: Optional[str] = None
    payload: str = ""      # исходное содержимое (html/json/text)
    url: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.utcnow)
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class BidEntity:
    """
    Нормализованная заявка (то, чем оперирует бизнес-логика).

    Важный момент: здесь нет прямой привязки к конкретной схеме БД.
    Поля подобраны на основе архитектурного описания и ТЗ.
    """
    id: Optional[int] = None
    source_id: int = 0
    raw_item_id: Optional[int] = None

    external_id: Optional[str] = None  # ID заявки на площадке
    title: str = ""
    description: str = ""

    cargo_type: Optional[str] = None
    transport_type: Optional[str] = None

    load_point: Optional[str] = None
    unload_point: Optional[str] = None

    weight_tons: Optional[float] = None
    price: Optional[float] = None
    currency: Optional[str] = None

    contact: Optional[str] = None
    url: Optional[str] = None

    published_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
