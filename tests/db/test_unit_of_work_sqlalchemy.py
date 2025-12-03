# path: tests/db/test_unit_of_work_sqlalchemy.py
from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import pytest

from dan_max_bids_parser.infrastructure.db.base import Base
from dan_max_bids_parser.infrastructure.db.models import Source
from dan_max_bids_parser.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork


def _make_session_factory():
    """
    Вспомогательная фабрика для SQLite in-memory.

    Создаёт временную БД, поднимает схему по Base.metadata
    и возвращает sessionmaker для использования в UoW.
    """
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _get_source_codes(session) -> set[str]:
    """
    Утилита для чтения всех кодов источников напрямую через SQLAlchemy.

    Здесь мы намеренно НЕ используем репозитории, чтобы в тесте
    проверять именно транзакционное поведение UoW, а не контракт
    конкретной реализации репозитория.
    """
    stmt = select(Source)
    result = session.execute(stmt)
    sources = result.scalars().all()
    return {s.code for s in sources}


def test_uow_commit_persists_changes():
    """
    Проверяем, что при явном commit() данные фиксируются в БД.

    Внутри контекста UoW:
    - создаём ORM-объект Source,
    - добавляем его в uow.session,
    - вызываем uow.commit().

    В новой сессии читаем содержимое таблицы и убеждаемся,
    что код источника присутствует.
    """
    SessionFactory = _make_session_factory()
    uow = SqlAlchemyUnitOfWork(session_factory=SessionFactory)

    with uow:
        src = Source(
            code="TEST_SRC",
            name="Test Source",
            kind="html",
            # остальные поля полагаемся на значения по умолчанию
        )
        uow.session.add(src)
        uow.commit()

    with SessionFactory() as session:
        codes = _get_source_codes(session)
        assert "TEST_SRC" in codes


def test_uow_without_commit_rolls_back_changes():
    """
    Проверяем, что без commit() изменения не попадают в БД.

    Внутри контекста:
    - добавляем Source в uow.session,
    - НЕ вызываем commit().

    При выходе из контекста UoW должен сделать rollback(),
    и в новой сессии этого источника быть не должно.
    """
    SessionFactory = _make_session_factory()
    uow = SqlAlchemyUnitOfWork(session_factory=SessionFactory)

    with uow:
        src = Source(
            code="NO_COMMIT",
            name="No Commit Source",
            kind="html",
        )
        uow.session.add(src)
        # commit() намеренно не вызываем

    with SessionFactory() as session:
        codes = _get_source_codes(session)
        assert "NO_COMMIT" not in codes


def test_uow_rollback_on_exception():
    """
    Проверяем, что при исключении внутри контекста все изменения откатываются.

    Внутри вложенного with uow:
    - добавляем Source в uow.session,
    - выбрасываем исключение.

    UoW обязан выполнить rollback(), и в новой сессии этого источника
    быть не должно.
    """
    SessionFactory = _make_session_factory()
    uow = SqlAlchemyUnitOfWork(session_factory=SessionFactory)

    with pytest.raises(RuntimeError):
        with uow:
            src = Source(
                code="WITH_EXCEPTION",
                name="Broken Source",
                kind="html",
            )
            uow.session.add(src)
            # Искусственно ломаем выполнение
            raise RuntimeError("boom")

    with SessionFactory() as session:
        codes = _get_source_codes(session)
        assert "WITH_EXCEPTION" not in codes
