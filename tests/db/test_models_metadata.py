# path: tests/db/test_models_metadata.py
"""
Проверка соответствия ORM-моделей таблицам БД.

- Все ключевые таблицы присутствуют в Base.metadata.
- __tablename__ моделей совпадают с ожидаемыми.
"""

from __future__ import annotations

from dan_max_bids_parser.infrastructure.db.base import Base
from dan_max_bids_parser.infrastructure.db import models  # noqa: F401


def test_metadata_contains_expected_tables() -> None:
    """
    После импорта моделей таблицы должны быть зарегистрированы в Base.metadata.
    """
    tables = set(Base.metadata.tables.keys())

    expected = {
        "sources",
        "raw_items",
        "bids",
        "jobs",
        "errors",
        "config_source",
        "config_filter_rule",
        "config_classifier",
        "config_dedup",
        "config_schedule",
        "config_antibot",
        "config_export",
    }

    missing = expected - tables
    assert not missing, f"В ORM metadata отсутствуют таблицы: {sorted(missing)}"
