# path: migrations/env.py
from __future__ import annotations

"""
Alembic env-модуль.

Задача:
- Брать DATABASE_URL из настроек приложения (dan_max_bids_parser.config.get_settings).
- Поддерживать offline/online режимы миграций.
- Работать и с локальным SQLite, и с продовым PostgreSQL в зависимости от env.
"""

from logging.config import fileConfig
from typing import Any, Dict

from alembic import context
from sqlalchemy import engine_from_config, pool

from dan_max_bids_parser.config import get_settings

# Это объект конфигурации Alembic, на основании alembic.ini
config = context.config

# Настройка логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Пока без MetaData, добавим позже, когда появятся модели ORM
target_metadata = None


def get_url() -> str:
    """
    Получаем URL БД из настроек приложения.

    Для локальной отладки это SQLite (sqlite:///./dan_max_bids.db),
    для продовой среды — PostgreSQL (postgresql+psycopg://...).
    """
    settings = get_settings()
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме.

    В этом режиме Alembic не создаёт соединения с БД, а просто
    генерирует SQL.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в online-режиме.

    Здесь создаётся реальное подключение к БД, и Alembic
    исполняет изменения.
    """
    configuration: Dict[str, Any] = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Точка входа Alembic
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
