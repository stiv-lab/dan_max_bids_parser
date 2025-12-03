# path: src/dan_max_bids_parser/infrastructure/composition/samosval_harvesting_factory.py

"""
Фабрики для сборки стека RunSourceHarvestingService для samosval.info.

Слой:
    infrastructure.composition — точка сборки адаптеров и сервисов для конкретных источников.
"""

from __future__ import annotations

from typing import Callable

from dan_max_bids_parser.application.use_cases.harvest_source_service import (
    RunSourceHarvestingService,
    UnitOfWorkFactory,
)
from dan_max_bids_parser.infrastructure.adapters.samosval_raw_item_provider_adapter import (
    SamosvalRawItemProviderAdapter,
)
from dan_max_bids_parser.infrastructure.http.html_client import RequestsHtmlClient
from dan_max_bids_parser.infrastructure.providers.samosval_raw_item_provider import (
    SamosvalRawItemProvider,
)


def build_samosval_run_source_harvesting_service(
    uow_factory: UnitOfWorkFactory,
    *,
    listings_url: str = "https://samosval.info/",
) -> RunSourceHarvestingService:
    """
    Собрать RunSourceHarvestingService для источника samosval.info.

    Args:
        uow_factory: фабрика UnitOfWork (создаёт новый UoW на каждый вызов use-case).
        listings_url: URL страницы со списком заявок.

    Returns:
        Экземпляр RunSourceHarvestingService, готовый к использованию.
    """
    html_client = RequestsHtmlClient()
    samosval_provider = SamosvalRawItemProvider(
        html_client=html_client,
        listings_url=listings_url,
    )
    adapter = SamosvalRawItemProviderAdapter(samosval_provider)

    return RunSourceHarvestingService(
        uow_factory=uow_factory,
        raw_item_provider=adapter,
    )
