# path: docs/architecture/dan_max_diagrams.md
# Архитектурные диаграммы системы Дан-Макс (Mermaid)

## 1. Слои архитектуры (Clean Architecture / Ports & Adapters)

```mermaid
flowchart LR
    subgraph Domain["Domain Layer"]
        D1["Модели: Bid, Source, RawItem"]
        D2["Сервисы: BidClassifier, Normalizer,<br/>BidFilter, BidDeduplicator"]
    end

    subgraph Application["Application Layer (Use Cases)"]
        A1["RunSourceHarvesting"]
        A2["ReprocessRawItems"]
        A3["ExportBids"]
        A4["GenerateDailyHealthReport"]
    end

    subgraph Interfaces["Interfaces Layer"]
        I1["CLI"]
        I2["REST API (этап 2+)"]
        I3["Web UI (этап 2+)"]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        INF1["DB (PostgreSQL, BidRepository,<br/>RawItemRepository, ConfigRepository)"]
        INF2["Source Adapters<br/>(HTML/API/Telegram/WhatsApp)"]
        INF3["Anti-bot & Proxy<br/>(ProxyManager, UserAgentProvider,<br/>CaptchaSolverPort)"]
        INF4["Export Adapters<br/>(XLSX, CSV, Google Sheets)"]
        INF5["Scheduler (cron/APScheduler,<br/>очереди задач)"]
        INF6["Monitoring & Alerts (Telegram,<br/>логи, метрики)"]
    end

    %% Направление зависимостей: внешний уровень -> внутренний
    I1 --> A1
    I1 --> A2
    I1 --> A3
    I2 --> A1
    I2 --> A3
    I3 --> A1
    I3 --> A4

    A1 --> D1
    A1 --> D2
    A2 --> D1
    A2 --> D2
    A3 --> D1
    A4 --> D1

    A1 --> INF2
    A1 --> INF1
    A2 --> INF1
    A3 --> INF4
    A4 --> INF6

    INF2 --> INF3
    INF5 --> A1
    INF5 --> A2
    INF5 --> A4
    INF6 --> I1
```

---

## 2. Модули системы (в разрезе архитектурных блоков)

```mermaid
flowchart TB
    subgraph Config["Config Layer (config_* в БД)"]
        C1["SourceConfig"]
        C2["FilterRuleConfig"]
        C3["ClassifierConfig"]
        C4["DeduplicationConfig"]
        C5["ScheduleConfig"]
        C6["AntiBotProfiles"]
        C7["ExportConfig"]
    end

    subgraph ETLCore["ETL Core (Domain + Application)"]
        E1["Extract<br/>(RawItemProvider)"]
        E2["Parse<br/>(HTML/JSON → RawItem)"]
        E3["Normalize<br/>(Normalizer: даты, города,<br/>цены, контакты)"]
        E4["Classify<br/>(BidClassifier: тип груза)"]
        E5["Filter<br/>(BidFilter: по грузу/маршруту/цене)"]
        E6["Deduplicate<br/>(BidDeduplicator)"]
        E7["Store<br/>(BidRepository, RawItemRepository)"]
    end

    subgraph SourceAdapters["Source Adapters Layer"]
        SA1["HTMLSiteAdapter<br/>(ATI, Perevozka24, и др.)"]
        SA2["TelegramAdapter<br/>(группы и каналы)"]
        SA3["WhatsAppAdapter<br/>(по тех. возможности)"]
        SA4["APISiteAdapter<br/>(если есть JSON/API)"]
    end

    subgraph Storage["Storage Layer"]
        S1["PostgreSQL DB"]
        S2["Таблицы: sources,<br/>raw_items, bids,<br/>config_*, jobs, errors"]
    end

    subgraph ExportLayer["Export Layer"]
        EX1["XLSXExporter"]
        EX2["GoogleSheetsExporter"]
        EX3["CSVExporter"]
    end

    subgraph SchedulerLayer["Scheduler Layer"]
        SCH1["SchedulerService<br/>(cron / APScheduler)"]
        SCH2["Очередь задач<br/>(этап 2: Celery/RQ)"]
    end

    subgraph Monitoring["Monitoring & Alerts"]
        M1["Logger (JSON-логи)"]
        M2["AlertingPort<br/>(Telegram)"]
        M3["Metrics (Prometheus/Grafana,<br/>этап 2+)"]
    end

    subgraph Interfaces["Interfaces"]
        IF1["CLI Tools<br/>(run_harvest, export, debug)"]
        IF2["REST API<br/>(поиск заявок и статусы)"]
        IF3["Web UI<br/>(панель управления)"]
    end

    %% Связи
    SA1 --> E1
    SA2 --> E1
    SA3 --> E1
    SA4 --> E1

    E1 --> E2 --> E3 --> E4 --> E5 --> E6 --> E7

    E7 --> S1
    S1 --> ETLCore

    Config --> ETLCore
    Config --> SourceAdapters
    Config --> SchedulerLayer
    Config --> ExportLayer
    Config --> Monitoring

    ExportLayer --> S1
    SchedulerLayer --> ETLCore
    Monitoring --> Interfaces

    Interfaces --> ETLCore
    Interfaces --> ExportLayer
```

---

## 3. ETL-потоки, привязанные к слоям и модулям

```mermaid
flowchart LR
    subgraph Sources["Источники (внешний мир)"]
        SRC1["ATI / Perevozka24 / другие сайты"]
        SRC2["Telegram-группы"]
        SRC3["WhatsApp-группы"]
    end

    subgraph Infra["Infrastructure Layer"]
        SA["SourceAdapter (HTML/Telegram/WhatsApp)"]
        AB["AntiBot Layer<br/>(ProxyManager, UserAgentProvider,<br/>CaptchaSolverPort)"]
        DB["PostgreSQL (Storage)"]
        EXP["Export Adapters<br/>(XLSX/Sheets/CSV)"]
    end

    subgraph App["Application Layer (Use Cases)"]
        UC1["RunSourceHarvesting(source_id)"]
        UC2["ReprocessRawItems()"]
        UC3["ExportBids()"]
        UC4["GenerateDailyHealthReport()"]
    end

    subgraph Domain["Domain Layer (ETL Core)"]
        D_EX["Extract<br/>(RawItemProvider)"]
        D_P["Parse<br/>(RawItemParser)"]
        D_N["Normalize<br/>(Normalizer)"]
        D_C["Classify<br/>(BidClassifier)"]
        D_F["Filter<br/>(BidFilter)"]
        D_D["Deduplicate<br/>(BidDeduplicator)"]
        D_S["Store<br/>(BidRepository, RawItemRepository)"]
    end

    subgraph Interfaces["Interfaces Layer"]
        CLI["CLI / Jobs"]
        API["REST API (этап 2+)"]
        UI["Web UI (этап 2+)"]
    end

    %% Поток EXTRACT
    SRC1 --> SA
    SRC2 --> SA
    SRC3 --> SA
    SA --> AB
    SA --> D_EX

    %% Поток ETL
    D_EX --> D_P --> D_N --> D_C --> D_F --> D_D --> D_S
    D_S --> DB

    %% Юз-кейсы и интерфейсы
    CLI --> UC1
    CLI --> UC2
    CLI --> UC3
    CLI --> UC4

    API --> UC1
    API --> UC3

    UI --> UC1
    UI --> UC3
    UI --> UC4

    UC1 --> D_EX
    UC2 --> D_N
    UC2 --> D_C
    UC2 --> D_F
    UC2 --> D_D
    UC2 --> D_S

    UC3 --> EXP
    EXP --> DB

    UC4 --> DB
```

---

## 4. Карта источников и структура адаптеров

```mermaid
flowchart TB
    subgraph Config["Config Layer (config.sources)"]
        CS1["SourceConfig: type=HTML_SITE,<br/>code=ATI"]
        CS2["SourceConfig: type=HTML_SITE,<br/>code=PEREVOZKA24"]
        CS3["SourceConfig: type=TG_GROUP,<br/>code=TG_SAMOSVALY"]
        CS4["SourceConfig: type=WA_GROUP,<br/>code=WA_SAMOSVALY"]
        CS5["SourceConfig: type=HTML_SITE,<br/>code=OTHER_SITE_X"]
    end

    subgraph Adapters["Source Adapters Layer"]
        SA_HTML["HTMLSiteAdapter<br/>(универсальный HTML/Web)"]
        SA_TG["TelegramAdapter<br/>(Telethon/Aiogram)"]
        SA_WA["WhatsAppAdapter<br/>(по возможности)"]
        SA_API["APISiteAdapter<br/>(JSON/API источники)"]
    end

    subgraph AntiBot["Anti-bot Layer"]
        AB1["ProxyManager"]
        AB2["UserAgentProvider"]
        AB3["RequestThrottler"]
        AB4["CaptchaSolverPort<br/>(опционально)"]
    end

    subgraph ETLExtract["ETL Extract"]
        E1["RawItemProvider<br/>(универсальный интерфейс)"]
    end

    %% Соответствие SourceConfig → адаптеры
    CS1 --> SA_HTML
    CS2 --> SA_HTML
    CS3 --> SA_TG
    CS4 --> SA_WA
    CS5 --> SA_HTML

    %% Адаптеры используют Anti-bot
    SA_HTML --> AB1
    SA_HTML --> AB2
    SA_HTML --> AB3
    SA_HTML --> AB4

    SA_API --> AB1
    SA_API --> AB2
    SA_API --> AB3
    SA_API --> AB4

    SA_TG --> AB3
    SA_WA --> AB3

    %% Все адаптеры отдают данные в единый ETL-вход
    SA_HTML --> E1
    SA_API --> E1
    SA_TG --> E1
    SA_WA --> E1
```

---
