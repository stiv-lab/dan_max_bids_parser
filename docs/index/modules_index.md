# path: docs/index/modules_index.md
# Индекс модулей проекта

> ВНИМАНИЕ: файл сгенерирован автоматически скриптом `tools/generate_module_index.py`.
> Не редактируйте этот файл вручную — изменения будут перезаписаны.

## src/dan_max_bids_parser/application/

### (корень слоя)

- `src/dan_max_bids_parser/application/unit_of_work.py`  
  Описание: Описание отсутствует

### use_cases/

- `src/dan_max_bids_parser/application/use_cases/harvest_source.py`  
  Описание: Описание отсутствует

- `src/dan_max_bids_parser/application/use_cases/harvest_source_service.py`  
  Описание: Описание отсутствует


## src/dan_max_bids_parser/config.py/

### (корень слоя)

- `src/dan_max_bids_parser/config.py`  
  Описание: Конфигурация приложения и параметры подключения к БД.


## src/dan_max_bids_parser/domain/

### (корень слоя)

- `src/dan_max_bids_parser/domain/entities.py`  
  Описание: Описание отсутствует

- `src/dan_max_bids_parser/domain/ports.py`  
  Описание: Описание отсутствует


## src/dan_max_bids_parser/infrastructure/

### db/

- `src/dan_max_bids_parser/infrastructure/db/base.py`  
  Описание: Базовая настройка SQLAlchemy для проекта Дан-Макс:

- `src/dan_max_bids_parser/infrastructure/db/models.py`  
  Описание: ORM-модели SQLAlchemy для схемы БД Дан-Макс (MVP):

- `src/dan_max_bids_parser/infrastructure/db/repositories.py`  
  Описание: Описание отсутствует

- `src/dan_max_bids_parser/infrastructure/db/unit_of_work.py`  
  Описание: Описание отсутствует

### http/

- `src/dan_max_bids_parser/infrastructure/http/html_client.py`  
  Описание: Описание отсутствует


## src/dan_max_bids_parser/interfaces/

### (корень слоя)

- `src/dan_max_bids_parser/interfaces/harvest_source_cli.py`  
  Описание: CLI-интерфейс для ручного запуска use-case RunSourceHarvesting.
