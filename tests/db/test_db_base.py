# path: tests/db/test_db_base.py
"""
Smoke-тест для инфраструктурного слоя БД:

- engine создаётся без ошибок;
- можно открыть и закрыть Session.
"""

from __future__ import annotations

from sqlalchemy import text

from dan_max_bids_parser.infrastructure.db.base import Base, SessionFactory, engine


def test_engine_connects() -> None:
    """
    Проверяем, что engine может установить соединение с БД и выполнить простой запрос.
    """
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        value = result.scalar_one()
        assert value == 1


def test_session_factory_works() -> None:
    """
    Проверяем, что SessionFactory создаёт сессию и она корректно закрывается.
    """
    session = SessionFactory()
    try:
        assert Base.metadata is not None
        value = session.execute(text("SELECT 1")).scalar_one()
        assert value == 1
    finally:
        session.close()
