# path: src/dan_max_bids_parser/config.py
"""
Конфигурация приложения и параметры подключения к БД.

Локально используем SQLite, в проде — PostgreSQL.
Все параметры считываем из окружения (DATABASE_URL), чтобы не жёстко
зашивать секреты и настройки.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Глобальные настройки приложения."""

    # Примеры:
    #   локальный SQLite:  sqlite+aiosqlite:///./dan_max_bids.db
    #   продовый Postgres: postgresql+psycopg://user:pass@host:port/dbname
    DATABASE_URL: str = "sqlite+aiosqlite:///./dan_max_bids.db"

    # Конфигурация загрузки env-файлов
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Ленивая инициализация настроек приложения."""
    return Settings()
