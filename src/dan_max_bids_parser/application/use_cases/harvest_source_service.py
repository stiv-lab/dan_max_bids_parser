# path: src/dan_max_bids_parser/application/use_cases/harvest_source_service.py
from __future__ import annotations

from collections.abc import Callable, Iterable

from dan_max_bids_parser.application.unit_of_work import UnitOfWork
from dan_max_bids_parser.domain.entities import BidEntity, RawItemEntity, SourceEntity
from dan_max_bids_parser.domain.ports import RawItemProviderPort
from .harvest_source import RunSourceHarvestingCommand, RunSourceHarvestingUseCase


UnitOfWorkFactory = Callable[[], UnitOfWork]


class RunSourceHarvestingService(RunSourceHarvestingUseCase):
    """
    Базовая реализация use-case RunSourceHarvesting.

    Шаги:
    1. Найти Source по коду.
    2. Получить сырые объекты через RawItemProviderPort.
    3. Сохранить RawItemEntity через RawItemRepositoryPort.
    4. На основе сохранённых raw_items создать простые BidEntity и сохранить их.
    """

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        raw_item_provider: RawItemProviderPort,
    ) -> None:
        """
        :param uow_factory: фабрика UnitOfWork (новый UoW на каждый вызов execute).
        :param raw_item_provider: порт внешнего провайдера сырых объектов.
        """
        self._uow_factory = uow_factory
        self._raw_item_provider = raw_item_provider

    def execute(self, command: RunSourceHarvestingCommand) -> None:
        """
        Запускает минимальный ETL-поток для одного источника.

        На данном этапе:
        - нет нормализации, фильтрации и дедупликации;
        - BidEntity создаются в простейшей форме из RawItemEntity.
        """
        with self._uow_factory() as uow:
            source = uow.sources.get_by_code(command.source_code)
            if source is None:
                raise ValueError(
                    f"Source with code='{command.source_code}' not found"
                )

            raw_items = self._load_raw_items(source)
            if not raw_items:
                # Нечего сохранять — выходим без ошибок.
                return

            saved_raw_items = list(uow.raw_items.add_many(raw_items))
            bids = list(self._build_bids_from_raw_items(source, saved_raw_items))

            if bids:
                uow.bids.add_many(bids)

            uow.commit()

    # --- Вспомогательные методы ---

    def _load_raw_items(self, source: SourceEntity) -> list[RawItemEntity]:
        """
        Загружает сырые объекты через RawItemProviderPort и
        нормализует минимально необходимые поля (source_id).
        """
        raw_items = list(self._raw_item_provider.fetch_raw_items(source))

        for item in raw_items:
            # Гарантируем заполнение source_id, если Source уже имеет id.
            if item.source_id == 0 and source.id is not None:
                item.source_id = source.id

        return raw_items

    def _build_bids_from_raw_items(
        self,
        source: SourceEntity,
        raw_items: Iterable[RawItemEntity],
    ) -> Iterable[BidEntity]:
        """
        Простейшее построение BidEntity из RawItemEntity.

        Здесь пока нет реальной логики нормализации/классификации —
        только демонстрация end-to-end потока.
        """
        for raw in raw_items:
            yield BidEntity(
                source_id=raw.source_id,
                raw_item_id=raw.id,
                external_id=raw.external_id,
                title=f"{source.name or source.code}: заявка "
                f"{raw.external_id or raw.id or ''}".strip(),
                description=raw.payload,
                url=raw.url,
            )
