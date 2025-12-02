"""initial_schema

Revision ID: 5f2851ddc47c
Revises: 
Create Date: 2025-12-02 17:56:07.555325

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f2851ddc47c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Таблица источников
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),  # site / telegram / whatsapp / api
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # Таблица сырых объектов
    op.create_table(
        "raw_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_raw_items_source_id", "raw_items", ["source_id"])
    op.create_index("ix_raw_items_external_id", "raw_items", ["external_id"])
    op.create_index("ix_raw_items_hash", "raw_items", ["hash"])

    # Таблица нормализованных заявок
    op.create_table(
        "bids",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("raw_item_id", sa.Integer(), sa.ForeignKey("raw_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cargo_type", sa.String(length=128), nullable=True),
        sa.Column("transport_type", sa.String(length=128), nullable=True),
        sa.Column("weight_value", sa.Numeric(precision=14, scale=3), nullable=True),
        sa.Column("weight_unit", sa.String(length=16), nullable=True),
        sa.Column("price_value", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("price_currency", sa.String(length=8), nullable=True),
        sa.Column("load_location", sa.String(length=255), nullable=True),
        sa.Column("unload_location", sa.String(length=255), nullable=True),
        sa.Column("load_region", sa.String(length=255), nullable=True),
        sa.Column("unload_region", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=64), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("dedup_key", sa.String(length=512), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_bids_source_id", "bids", ["source_id"])
    op.create_index("ix_bids_external_id", "bids", ["external_id"])
    op.create_index("ix_bids_dedup_key", "bids", ["dedup_key"])

    # Таблица задач (jobs)
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_total", sa.Integer(), nullable=True),
        sa.Column("items_created", sa.Integer(), nullable=True),
        sa.Column("items_updated", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_jobs_source_id", "jobs", ["source_id"])
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])

    # Таблица ошибок
    op.create_table(
        "errors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="error"),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_errors_source_id", "errors", ["source_id"])
    op.create_index("ix_errors_job_id", "errors", ["job_id"])
    op.create_index("ix_errors_severity", "errors", ["severity"])

    # Унифицированный паттерн для таблиц конфигурации
    def create_config_table(table_name: str) -> None:
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=128), nullable=False, unique=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("data", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    for cfg_table in (
        "config_source",
        "config_filter_rule",
        "config_classifier",
        "config_dedup",
        "config_schedule",
        "config_antibot",
        "config_export",
    ):
        create_config_table(cfg_table)


def downgrade() -> None:
    # Удаляем конфигурационные таблицы
    for cfg_table in (
        "config_export",
        "config_antibot",
        "config_schedule",
        "config_dedup",
        "config_classifier",
        "config_filter_rule",
        "config_source",
    ):
        op.drop_table(cfg_table)

    # Таблицы ошибок и jobs
    op.drop_index("ix_errors_severity", table_name="errors")
    op.drop_index("ix_errors_job_id", table_name="errors")
    op.drop_index("ix_errors_source_id", table_name="errors")
    op.drop_table("errors")

    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_index("ix_jobs_source_id", table_name="jobs")
    op.drop_table("jobs")

    # Таблица bids
    op.drop_index("ix_bids_dedup_key", table_name="bids")
    op.drop_index("ix_bids_external_id", table_name="bids")
    op.drop_index("ix_bids_source_id", table_name="bids")
    op.drop_table("bids")

    # Таблица raw_items
    op.drop_index("ix_raw_items_hash", table_name="raw_items")
    op.drop_index("ix_raw_items_external_id", table_name="raw_items")
    op.drop_index("ix_raw_items_source_id", table_name="raw_items")
    op.drop_table("raw_items")

    # Таблица sources
    op.drop_table("sources")

