# path: src/dan_max_bids_parser/infrastructure/adapters/samosval_raw_item_provider_adapter.py

"""
Адаптер: SamosvalRawItemProviderAdapter.

Назначение:
    - связать HTML-провайдер samosval.info с доменным портом RawItemProviderPort;
    - маппить SamosvalListingRaw → RawItemEntity в виде JSON payload.

Слой:
    infrastructure.adapters — часть внешних адаптеров.

Не выполняет:
    - запись в БД,
    - работу с UnitOfWork,
    - нормализацию данных.
"""

from __future__ import annotations

import json
from typing import Iterable, List

from dan_max_bids_parser.domain.entities import RawItemEntity, SourceEntity
from dan_max_bids_parser.domain.ports import RawItemProviderPort
from dan_max_bids_parser.infrastructure.parsers.samosval_html_parser import (
    SamosvalListingRaw,
)
from dan_max_bids_parser.infrastructure.providers.samosval_raw_item_provider import (
    SamosvalRawItemProvider,
)


class SamosvalRawItemProviderAdapter(RawItemProviderPort):
    """
    Инфраструктурный адаптер уровня raw-items.

    Задача:
        - запрашивать список SamosvalListingRaw у SamosvalRawItemProvider,
        - маппить их в RawItemEntity по согласованной JSON-схеме.
    """

    def __init__(self, provider: SamosvalRawItemProvider) -> None:
        self._provider = provider

    def fetch_raw_items(
        self, source: SourceEntity
    ) -> Iterable[RawItemEntity]:
        """
        Загрузить SamosvalListingRaw и преобразовать в RawItemEntity.

        Note:
            source_id устанавливается в use-case (RunSourceHarvestingService._load_raw_items),
            поэтому здесь выставляем source_id = 0.
        """
        listings: List[SamosvalListingRaw] = self._provider.fetch_listings()

        result: List[RawItemEntity] = []
        for item in listings:
            payload_dict = {
                "external_id": item.external_id,
                "title": item.title,
                "route_from": item.route_from,
                "route_to": item.route_to,
                "weight": item.weight,
                "price": item.price,
                "meta_raw": item.meta_raw,
                "url": item.url,
            }

            raw = RawItemEntity(
                source_id=0,  # будет заполнено в use-case
                external_id=item.external_id,
                payload=json.dumps(payload_dict, ensure_ascii=False),
                url=item.url,
            )
            result.append(raw)

        return result
