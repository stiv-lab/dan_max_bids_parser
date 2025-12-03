# path: src/dan_max_bids_parser/interfaces/harvest_source_cli.py
"""
CLI-интерфейс для ручного запуска use-case RunSourceHarvesting.

Пример использования (из корня проекта):

    poetry run python -m dan_max_bids_parser.interfaces.harvest_source_cli --source-code ATI

На данном этапе CLI использует простого StubRawItemProvider, который
генерирует тестовые RawItemEntity, чтобы продемонстрировать end-to-end поток:
Source -> RawItem -> Bid через SqlAlchemyUnitOfWork.
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime
from typing import Iterable, Optional, Sequence

from dan_max_bids_parser.config import get_settings
from dan_max_bids_parser.application.use_cases.harvest_source import (
    RunSourceHarvestingCommand,
)
from dan_max_bids_parser.application.use_cases.harvest_source_service import (
    RunSourceHarvestingService,
)
from dan_max_bids_parser.application.unit_of_work import UnitOfWork
from dan_max_bids_parser.domain.entities import RawItemEntity, SourceEntity
from dan_max_bids_parser.domain.ports import RawItemProviderPort

# ВАЖНО:
# Сначала инициализируем настройки и окружение (DATABASE_URL),
# а уже затем импортируем infrastructure.db.base, где создаётся engine.
_settings = get_settings()
os.environ.setdefault("DATABASE_URL", _settings.DATABASE_URL)

from dan_max_bids_parser.infrastructure.db.base import SessionFactory  # noqa: E402
from dan_max_bids_parser.infrastructure.db.unit_of_work import (  # noqa: E402
    SqlAlchemyUnitOfWork,
)


logger = logging.getLogger(__name__)


class StubRawItemProvider(RawItemProviderPort):
    """
    Простейший провайдер сырых объектов.

    Генерирует 1–2 тестовых RawItemEntity, чтобы можно было:
    - проверить wiring UoW + use-case;
    - увидеть, что данные проходят через весь ETL-поток и попадают в БД.

    В будущем этот провайдер будет заменён на реальные HTML/Telegram/API-адаптеры.
    """

    def fetch_raw_items(self, source: SourceEntity) -> Iterable[RawItemEntity]:
        now = datetime.utcnow()

        # В реальной реализации здесь будет парсинг HTML/JSON/сообщений.
        payload_text = (
            f"Stub payload for source {source.code} "
            f"at {now.isoformat(timespec='seconds')}"
        )

        # source.id может быть None, если источник только что создан и не сохранён,
        # но в нашем CLI предполагаем, что источники уже заведены в БД.
        source_id = source.id or 0

        return [
            RawItemEntity(
                source_id=source_id,
                external_id=f"stub-{source.code}-{now:%Y%m%d%H%M%S}",
                payload=payload_text,
                url=None,
                created_at=now,
                received_at=now,
            )
        ]


def _create_uow_factory() -> callable:
    """
    Фабрика UnitOfWork для CLI.

    Использует глобальный SessionFactory из infrastructure.db.base.
    """
    def factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(SessionFactory)

    return factory


def _build_service() -> RunSourceHarvestingService:
    """
    Собирает RunSourceHarvestingService для использования в CLI.
    """
    uow_factory = _create_uow_factory()
    raw_item_provider = StubRawItemProvider()
    return RunSourceHarvestingService(
        uow_factory=uow_factory,
        raw_item_provider=raw_item_provider,
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """
    Разбор аргументов командной строки для CLI.

    Сейчас поддерживается один сценарий:
        --source-code <CODE>
    """
    parser = argparse.ArgumentParser(
        prog="dan_max_bids_harvest",
        description=(
            "Запуск ETL-потока для конкретного источника (RunSourceHarvestingUseCase)."
        ),
    )
    parser.add_argument(
        "--source-code",
        required=True,
        help="Код источника (Source.code), для которого нужно запустить harvesting.",
    )
    return parser.parse_args(argv)


def run_harvest(source_code: str) -> None:
    """
    Высокоуровневая функция запуска harvesting для одного источника.

    Вынесена отдельно, чтобы её можно было вызывать из тестов без CLI-обвязки.
    """
    service = _build_service()
    command = RunSourceHarvestingCommand(source_code=source_code)

    logger.info("Starting harvesting for source_code=%s", source_code)
    service.execute(command)
    logger.info("Harvesting completed successfully for source_code=%s", source_code)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Точка входа CLI.

    Возвращает код выхода:
    - 0 при успешном завершении;
    - 1 при ошибках (например, источник не найден).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        args = parse_args(argv)
        run_harvest(args.source_code)
        print(f"Harvesting finished for source_code='{args.source_code}'")
        return 0
    except ValueError as exc:
        # Ожидаемые бизнес-ошибки (например, источник не найден)
        logger.error("Business error during harvesting: %s", exc)
        print(f"ERROR: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        # Непредвиденные ошибки
        logger.exception("Unexpected error during harvesting")
        print(f"UNEXPECTED ERROR: {exc}")
        return 1


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(main(sys.argv[1:]))
