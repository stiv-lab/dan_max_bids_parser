# path: src/dan_max_bids_parser/infrastructure/db/unit_of_work.py
from __future__ import annotations

from collections.abc import Callable
from typing import Optional, TypeVar

from sqlalchemy.orm import Session

from dan_max_bids_parser.application.unit_of_work import UnitOfWork
from dan_max_bids_parser.domain.ports import (
    SourceRepositoryPort,
    RawItemRepositoryPort,
    BidRepositoryPort,
)
from dan_max_bids_parser.infrastructure.db.repositories import (
    SqlAlchemySourceRepository,
    SqlAlchemyRawItemRepository,
    SqlAlchemyBidRepository,
)

# Тип фабрики сессий: совместим с любым sessionmaker, возвращающим Session
SessionFactory = Callable[[], Session]

_TSessionCo = TypeVar("_TSessionCo", bound=Session)


class SqlAlchemyUnitOfWork(UnitOfWork):
    """
    Реализация UnitOfWork поверх SQLAlchemy.

    Поведение:
    - Вход в контекст (with uow:) создаёт новую Session и репозитории.
    - commit() явно фиксирует транзакцию и помечает UoW как "committed".
    - rollback() откатывает текущую транзакцию (если есть).
    - При выходе из контекста:
      * если было исключение — выполняется rollback();
      * если исключения не было, но commit() не вызывался — выполняется rollback()
        (тем самым изменения без явного commit не попадают в БД);
      * в любом случае сессия закрывается.
    """

    # Атрибуты, ожидаемые протоколом UnitOfWork
    sources: SourceRepositoryPort
    raw_items: RawItemRepositoryPort
    bids: BidRepositoryPort

    def __init__(self, session_factory: SessionFactory) -> None:
        """
        :param session_factory: фабрика SQLAlchemy Session, например:
            SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
            uow = SqlAlchemyUnitOfWork(SessionLocal)
        """
        self._session_factory: SessionFactory = session_factory
        self._session: Optional[Session] = None
        self._committed: bool = False

    # --- Вспомогательные свойства ---

    @property
    def session(self) -> Session:
        """
        Текущая активная Session.

        :raises RuntimeError: если UoW ещё не вошёл в контекст.
        """
        if self._session is None:
            raise RuntimeError("SqlAlchemyUnitOfWork is not entered (no active session).")
        return self._session

    # --- Контекстный менеджер ---

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self._committed = False

        # Инициализация репозиториев на базе свежей сессии
        self.sources = SqlAlchemySourceRepository(self.session)
        self.raw_items = SqlAlchemyRawItemRepository(self.session)
        self.bids = SqlAlchemyBidRepository(self.session)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if exc_type is not None:
                # При исключении всегда откатываем транзакцию
                self.rollback()
            elif not self._committed:
                # Без явного commit() ничего не фиксируем
                self.rollback()
        finally:
            if self._session is not None:
                self._session.close()
            self._session = None

    # --- Управление транзакцией ---

    def commit(self) -> None:
        """
        Явная фиксация транзакции.

        После успешного commit флаг _committed устанавливается в True,
        чтобы __exit__ не откатывал изменения.
        """
        if self._session is None:
            raise RuntimeError("Cannot commit: SqlAlchemyUnitOfWork is not active.")
        self._session.commit()
        self._committed = True

    def rollback(self) -> None:
        """
        Откат текущей транзакции.
        """
        if self._session is not None:
            self._session.rollback()
