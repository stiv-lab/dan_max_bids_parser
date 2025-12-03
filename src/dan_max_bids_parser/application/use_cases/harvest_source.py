# path: src/dan_max_bids_parser/application/use_cases/harvest_source.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class RunSourceHarvestingCommand:
    """
    Команда для запуска ETL по конкретному источнику.

    На уровне интерфейса достаточно идентификации источника
    через code (человеко-читаемый идентификатор, уникальный).
    При необходимости позже расширим полями (ограничения по времени,
    режим dry-run и т.п.).
    """
    source_code: str


class RunSourceHarvestingUseCase(Protocol):
    """
    Контракт для use-case "RunSourceHarvesting".

    Application-слой реализует этот протокол, инфраструктура только
    инжектирует зависимости (UnitOfWork, адаптеры источников и т.п.).
    """

    def execute(self, command: RunSourceHarvestingCommand) -> None:
        """
        Запускает полный ETL-процесс для одного источника.

        Детали реализации (парсинг, нормализация, фильтрация,
        дедупликация и сохранение) будут реализованы позже.
        """
        ...
