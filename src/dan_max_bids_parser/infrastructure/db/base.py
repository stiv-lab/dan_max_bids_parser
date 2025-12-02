# path: src/dan_max_bids_parser/infrastructure/db/base.py
"""
Базовая настройка SQLAlchemy для проекта Дан-Макс:

- определение Base для ORM-моделей;
- фабрика движка на основе DATABASE_URL;
- SessionFactory для работы с БД.

Логика:
1. DATABASE_URL читается из переменной окружения;
2. если не задан, используется локальный SQLite (dev.sqlite в корне репозитория);
3. модуль не содержит доменной логики, только инфраструктуру.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

logger = logging.getLogger(__name__)

# Базовый класс для всех ORM-моделей инфраструктурного слоя
Base = declarative_base()


def _get_repo_root() -> Path:
    """
    Пытается найти корень репозитория, двигаясь вверх по дереву
    от текущего файла и ища pyproject.toml.
    Если не найден — берём самый верхний родитель.
    """
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return current.parents[-1]


def _default_sqlite_url() -> str:
    """
    Возвращает URL для локальной SQLite по умолчанию.

    Файл dev.sqlite создаётся в корне репозитория.
    Это поведение подходит для локальной разработки и тестов.
    """
    repo_root = _get_repo_root()
    db_path = repo_root / "dev.sqlite"
    return f"sqlite:///{db_path}"


def get_database_url() -> str:
    """
    Единая точка получения DATABASE_URL для приложения.

    Приоритет:
    1) env var DATABASE_URL;
    2) локальный SQLite dev.sqlite в корне репозитория.

    Важно: никаких захардкоженных кредов для PostgreSQL.
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url and "://" in env_url:
        return env_url

    default_url = _default_sqlite_url()
    logger.warning(
        "DATABASE_URL не задан, используется SQLite по умолчанию: %s",
        default_url,
    )
    return default_url


def create_engine_from_env() -> Engine:
    """
    Создаёт SQLAlchemy Engine на основе DATABASE_URL.

    Engine создаётся в синхронном режиме (обычный create_engine),
    что достаточно для текущих задач ETL и небольшого числа пользователей.
    """
    db_url = get_database_url()
    engine = create_engine(
        db_url,
        echo=False,
        future=True,
    )
    return engine


# Глобальный engine и фабрика сессий для приложения
engine: Engine = create_engine_from_env()

SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_session() -> Generator[Session, None, None]:
    """
    Контекстный генератор сессии.

    Подходит как для ручного использования, так и для интеграции с FastAPI (Depends),
    если будем использовать синхронные эндпоинты.
    """
    session: Session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
