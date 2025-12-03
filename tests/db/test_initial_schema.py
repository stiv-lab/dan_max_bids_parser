# path: tests/db/test_initial_schema.py
"""
Проверка, что начальная схема БД (initial_schema) применена корректно:
- все ожидаемые таблицы созданы;
- ключевые столбцы присутствуют.

Тесты используют тот же DATABASE_URL, что и приложение:
1) env var DATABASE_URL;
2) модуль dan_max_bids_parser.config.

alembic.ini здесь намеренно НЕ используется, т.к. в нём может быть заглушка.
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import inspect
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import NoSuchModuleError
from sqlalchemy import inspect


def _get_db_url_from_app_config() -> Optional[str]:
    """
    Пытается вытащить URL БД из модуля конфигурации приложения:
    dan_max_bids_parser.config.

    Мы не делаем жёстких предположений о структуре, а ищем строку, похожую на URL.
    """
    try:
        import dan_max_bids_parser.config as app_config  # type: ignore[import]
    except ImportError:
        return None

    # 1. Явные популярные имена
    candidate_names = ("DATABASE_URL", "database_url", "DB_URL", "db_url")
    for name in candidate_names:
        if hasattr(app_config, name):
            value = getattr(app_config, name)
            if isinstance(value, str) and "://" in value:
                return value

    # 2. Любая строка с "://"
    for name in dir(app_config):
        value = getattr(app_config, name)
        if isinstance(value, str) and "://" in value:
            return value
        # 3. Объект с атрибутом database_url
        if hasattr(value, "database_url"):
            url = getattr(value, "database_url")
            if isinstance(url, str) and "://" in url:
                return url

    return None


def _resolve_database_url() -> str:
    """
    Единая точка получения DATABASE_URL для тестов.
    Приоритет:
    1) env var DATABASE_URL;
    2) модуль dan_max_bids_parser.config.

    Если не найдено — явно падаем с понятной ошибкой.
    """
    # 1. Переменная окружения
    env_url = os.getenv("DATABASE_URL")
    if env_url and "://" in env_url:
        return env_url

    # 2. Конфиг приложения
    cfg_url = _get_db_url_from_app_config()
    if cfg_url and "://" in cfg_url:
        return cfg_url

    raise RuntimeError(
        "Не удалось определить URL БД для тестов. "
        "Установите переменную окружения DATABASE_URL, например:\n"
        "  export DATABASE_URL=sqlite:///./dev.sqlite\n"
        "или добавьте строковый DATABASE_URL/database_url в модуль dan_max_bids_parser.config."
    )


def _create_engine() -> Engine:
    db_url = _resolve_database_url()

    try:
        engine = create_engine(db_url)
    except NoSuchModuleError as exc:
        msg = (
            f"Не удалось создать Engine для URL '{db_url}'. "
            "Проверьте, что используется валидный dialect+driver, например:\n"
            "  sqlite:///./dev.sqlite\n"
            "  postgresql+psycopg://user:pass@host/dbname\n"
        )
        raise RuntimeError(msg) from exc

    return engine


def test_initial_schema_tables_exist() -> None:
    """
    Проверяем, что все ожидаемые таблицы созданы миграцией initial_schema.
    """
    engine = _create_engine()
    inspector = inspect(engine)

    tables = set(inspector.get_table_names())

    expected_tables = {
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

    missing = expected_tables - tables
    assert not missing, f"Отсутствуют ожидаемые таблицы: {sorted(missing)}"


def test_sources_table_columns() -> None:
    engine = _create_engine()
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("sources")}

    expected = {
        "id",
        "code",
        "name",
        "kind",         # вместо старого type
        "is_enabled",   # физическое поле (domain: is_active)
        "description",
        "created_at",
        "updated_at",
    }

    missing = expected - columns
    assert not missing, f"В таблице sources отсутствуют колонки: {sorted(missing)}"



def test_bids_table_columns() -> None:
    """
    Минимальная проверка структуры таблицы bids.
    """
    engine = _create_engine()
    inspector = inspect(engine)

    columns = {col["name"] for col in inspector.get_columns("bids")}

    expected_columns = {
        "id",
        "source_id",
        "raw_item_id",
        "external_id",
        "title",
        "cargo_type",
        "price_value",
        "price_currency",
        "load_location",
        "unload_location",
        "published_at",
        "dedup_key",
        "is_duplicate",
        "created_at",
        "updated_at",
    }

    missing = expected_columns - columns
    assert not missing, f"В таблице bids отсутствуют колонки: {sorted(missing)}"
