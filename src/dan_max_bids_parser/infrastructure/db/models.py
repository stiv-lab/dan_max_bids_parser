# path: src/dan_max_bids_parser/infrastructure/db/models.py
"""
ORM-модели SQLAlchemy для схемы БД Дан-Макс (MVP):

Таблицы:
- sources
- raw_items
- bids
- jobs
- errors
- config_source
- config_filter_rule
- config_classifier
- config_dedup
- config_schedule
- config_antibot
- config_export

Модели соответствуют уже созданной схеме (см. initial_schema миграцию).
Изменение структуры таблиц делается через Alembic, а не здесь.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dan_max_bids_parser.infrastructure.db.base import Base


# Для кросс-совместимости JSON-типа:
# - на PostgreSQL будет использоваться нативный JSON/JSONB,
# - на SQLite — JSON с dialect-спецификой (TEXT + функции).
JSONType = SQLiteJSON


class Source(Base):
    __tablename__ = "sources"

    id = sa.Column(sa.Integer, primary_key=True)
    code = sa.Column(sa.String(50), nullable=False, unique=True, index=True)
    name = sa.Column(sa.String(255), nullable=False)

    # Доменное поле kind (html / telegram / api / ...).
    # В БД колонка называется kind (после миграции-rename).
    kind = sa.Column(sa.String(50), nullable=False, index=True)

    # Физический столбец в таблице: is_enabled, атрибут домена: is_active.
    is_active = sa.Column(
        "is_enabled",
        sa.Boolean,
        nullable=False,
        server_default=sa.true(),
    )

    # Описание источника (domain: description).
    description = sa.Column(sa.Text, nullable=True)

    # тех. поля аудита: по умолчанию заполняем текущим временем на уровне ORM
    created_at = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at = sa.Column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # --- Обратные связи для ORM-моделей ---

    raw_items = relationship(
        "RawItem",
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    bids = relationship(
        "Bid",
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    jobs = relationship(
        "Job",
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    errors = relationship(
        "ErrorLog",
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RawItem(Base):
    """Сырой объект, полученный при парсинге (HTML, JSON, сообщение)."""

    __tablename__ = "raw_items"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[Optional[str]] = mapped_column(sa.String(128), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(sa.String(1024), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="new")
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    hash: Mapped[Optional[str]] = mapped_column(sa.String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    # Связи
    source: Mapped[Source] = relationship(back_populates="raw_items")
    bids: Mapped[List["Bid"]] = relationship(
        back_populates="raw_item",
        cascade="all",
        passive_deletes=True,
    )


class Bid(Base):
    """Нормализованная заявка на перевозку."""

    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    raw_item_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer,
        sa.ForeignKey("raw_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    external_id: Mapped[Optional[str]] = mapped_column(sa.String(128), nullable=True)
    title: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    cargo_type: Mapped[Optional[str]] = mapped_column(sa.String(128), nullable=True)
    transport_type: Mapped[Optional[str]] = mapped_column(sa.String(128), nullable=True)
    weight_value: Mapped[Optional[float]] = mapped_column(
        sa.Numeric(14, 3),
        nullable=True,
    )
    weight_unit: Mapped[Optional[str]] = mapped_column(sa.String(16), nullable=True)
    price_value: Mapped[Optional[float]] = mapped_column(
        sa.Numeric(14, 2),
        nullable=True,
    )
    price_currency: Mapped[Optional[str]] = mapped_column(sa.String(8), nullable=True)
    load_location: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    unload_location: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    load_region: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    unload_region: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    contact_name: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(sa.String(64), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(sa.String(1024), nullable=True)
    dedup_key: Mapped[Optional[str]] = mapped_column(sa.String(512), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    # Связи
    source: Mapped[Source] = relationship(back_populates="bids")
    raw_item: Mapped[Optional[RawItem]] = relationship(back_populates="bids")


class Job(Base):
    """Запуск фоновой задачи (парсинг, экспорт, очистка и т.д.)."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    source_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer,
        sa.ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        default="pending",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    items_total: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    items_created: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    items_updated: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    source: Mapped[Optional[Source]] = relationship(back_populates="jobs")
    errors: Mapped[List["ErrorLog"]] = relationship(
        back_populates="job",
        cascade="all",
        passive_deletes=True,
    )


class ErrorLog(Base):
    """Критическая ошибка/событие, связанное с источником или задачей."""

    __tablename__ = "errors"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    source_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer,
        sa.ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer,
        sa.ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        default="error",
    )
    message: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )

    source: Mapped[Optional[Source]] = relationship(back_populates="errors")
    job: Mapped[Optional[Job]] = relationship(back_populates="errors")


# --- Конфигурационные таблицы ---


class ConfigBaseMixin:
    """
    Общие поля для конфигурационных таблиц.

    Используется только как mixin, __tablename__ определяется в конкретных моделях.
    """

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    code: Mapped[str] = mapped_column(sa.String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
    )
    data: Mapped[dict] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )


class ConfigSource(Base, ConfigBaseMixin):
    """Расширенная конфигурация источников (пагинация, селекторы, параметры)."""

    __tablename__ = "config_source"


class ConfigFilterRule(Base, ConfigBaseMixin):
    """Правила фильтрации заявок (тип груза, маршрут, цена и т.п.)."""

    __tablename__ = "config_filter_rule"


class ConfigClassifier(Base, ConfigBaseMixin):
    """Конфигурация классификатора (словари, правила, регексы)."""

    __tablename__ = "config_classifier"


class ConfigDedup(Base, ConfigBaseMixin):
    """Конфигурация стратегий дедупликации."""

    __tablename__ = "config_dedup"


class ConfigSchedule(Base, ConfigBaseMixin):
    """Правила расписания задач (cron/interval, backoff)."""

    __tablename__ = "config_schedule"


class ConfigAntibot(Base, ConfigBaseMixin):
    """Профили антибот-поведения (прокси, UA, лимиты)."""

    __tablename__ = "config_antibot"


class ConfigExport(Base, ConfigBaseMixin):
    """Настройки экспортов (XLSX, Google Sheets и т.п.)."""

    __tablename__ = "config_export"
