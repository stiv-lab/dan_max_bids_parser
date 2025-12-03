# path: tools/generate_module_index.py
"""
Скрипт генерации индексного файла модулей проекта.

Обходит исходники в src/ (и, при желании, tests/), собирает список .py файлов
и формирует Markdown-индекс:

- группировка по "слою" / директории (например, src/dan_max_bids_parser/domain),
- внутри — поддиректории (entities, services и т.п.),
- для каждого файла: относительный путь и краткое описание.

Описание берётся:
1) из module docstring (первая строка),
2) либо из первого осмысленного комментария после строки `# path: ...`,
3) если ничего не найдено — ставится заглушка "Описание отсутствует".

Файл результата: docs/index/modules_index.md
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


# PROJECT_ROOT — корень репозитория (каталог, где лежит pyproject.toml, src, tests, tools и т.п.)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Каталоги, которые считаем "исходниками" для индекса
SOURCE_ROOTS = [
    PROJECT_ROOT / "src",
    # при необходимости позже можно добавить:
    # PROJECT_ROOT / "tests",
]

INDEX_PATH = PROJECT_ROOT / "docs" / "index" / "modules_index.md"

# Игнорируемые директории и файлы
IGNORE_DIR_NAMES = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "build",
    "dist",
    ".eggs",
}

# При желании можно исключить миграции Alembic и т.п.
IGNORE_PATH_SUBSTRINGS = {
    "/migrations/",
    "/alembic/",
}

# Игнорируемые файлы по имени
IGNORE_FILE_NAMES = {
    "__init__.py",
}


@dataclass
class ModuleInfo:
    rel_path: Path
    description: str


def is_ignored_dir(path: Path) -> bool:
    return any(part in IGNORE_DIR_NAMES for part in path.parts)


def is_ignored_file(path: Path) -> bool:
    if path.name in IGNORE_FILE_NAMES:
        return True
    rel = str(path.as_posix())
    return any(sub in rel for sub in IGNORE_PATH_SUBSTRINGS)


def discover_python_files() -> List[Path]:
    """Находит все .py файлы в указанных SOURCE_ROOTS с учётом фильтров."""
    files: List[Path] = []
    for root in SOURCE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if is_ignored_dir(path.parent):
                continue
            if is_ignored_file(path):
                continue
            files.append(path)
    return sorted(files)


def extract_description(path: Path) -> str:
    """
    Извлекает краткое описание модуля.

    Приоритет:
    1) первая строка из module docstring,
    2) первый комментарий после строки `# path: ...`,
    3) "Описание отсутствует".
    """
    try:
        source_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "Описание отсутствует (ошибка декодирования файла)"

    description: str | None = None

    # 1. Пробуем module docstring через ast
    try:
        module = ast.parse(source_text)
        docstring = ast.get_docstring(module, clean=True)
        if docstring:
            first_line = docstring.strip().splitlines()[0].strip()
            if first_line:
                description = first_line
    except SyntaxError:
        # файл может быть невалидным во время разработки — просто игнорируем
        pass

    if description:
        return description

    # 2. Ищем первый осмысленный комментарий после `# path: ...`
    lines = source_text.splitlines()
    found_path_line = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# path:"):
            found_path_line = True
            continue

        if not found_path_line:
            continue

        if stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()
            if candidate:
                description = candidate
                break

        # Если встретили непустую строку кода/докстринга — прекращаем поиск
        if stripped and not stripped.startswith("#"):
            break

    if description:
        return description

    return "Описание отсутствует"


def group_modules(modules: List[ModuleInfo]) -> Dict[str, Dict[str, List[ModuleInfo]]]:
    """
    Группирует модули по "слою" и поддиректориям.

    Логика:
    - layer_key: первые 2–3 компонента пути
      (например, src/dan_max_bids_parser/domain или src/dan_max_bids_parser/infrastructure)
    - subdir_key: оставшаяся часть директории (например, entities, services)
    """
    grouped: Dict[str, Dict[str, List[ModuleInfo]]] = {}

    for mi in modules:
        parts = mi.rel_path.parts
        # например: ("src", "dan_max_bids_parser", "domain", "entities", "bid.py")

        if len(parts) >= 3:
            layer_key = "/".join(parts[:3])  # src/dan_max_bids_parser/domain
            remaining_dir_parts = parts[3:-1]
        elif len(parts) == 2:
            layer_key = "/".join(parts[:2])
            remaining_dir_parts = []
        else:
            layer_key = parts[0]
            remaining_dir_parts = []

        subdir_key = "/".join(remaining_dir_parts) if remaining_dir_parts else ""

        grouped.setdefault(layer_key, {}).setdefault(subdir_key, []).append(mi)

    # Сортировка внутри групп
    for layer_key in grouped:
        for subdir_key in grouped[layer_key]:
            grouped[layer_key][subdir_key].sort(key=lambda m: str(m.rel_path))

    return grouped


def build_markdown(modules: List[ModuleInfo]) -> str:
    """Формирует содержимое Markdown-файла с индексом модулей."""
    grouped = group_modules(modules)

    lines: List[str] = []
    lines.append("# path: docs/index/modules_index.md")
    lines.append("# Индекс модулей проекта")
    lines.append("")
    lines.append("> ВНИМАНИЕ: файл сгенерирован автоматически скриптом `tools/generate_module_index.py`.")
    lines.append("> Не редактируйте этот файл вручную — изменения будут перезаписаны.")
    lines.append("")

    for layer_key in sorted(grouped.keys()):
        lines.append(f"## {layer_key}/")
        lines.append("")

        subdirs = grouped[layer_key]
        # Пустые subdir (файлы прямо в layer-директории) выводим первыми
        if "" in subdirs:
            lines.append("### (корень слоя)")
            lines.append("")
            for mi in subdirs[""]:
                rel_str = mi.rel_path.as_posix()
                lines.append(f"- `{rel_str}`  ")
                lines.append(f"  Описание: {mi.description}")
                lines.append("")
            # убираем, чтобы не повторять
            subdirs = {k: v for k, v in subdirs.items() if k != ""}

        for subdir_key in sorted(subdirs.keys()):
            if subdir_key:
                lines.append(f"### {subdir_key}/")
                lines.append("")
            for mi in subdirs[subdir_key]:
                rel_str = mi.rel_path.as_posix()
                lines.append(f"- `{rel_str}`  ")
                lines.append(f"  Описание: {mi.description}")
                lines.append("")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    # Убеждаемся, что директория для индекса существует
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    py_files = discover_python_files()
    modules: List[ModuleInfo] = []

    for path in py_files:
        rel_path = path.relative_to(PROJECT_ROOT)
        description = extract_description(path)
        modules.append(ModuleInfo(rel_path=rel_path, description=description))

    new_content = build_markdown(modules)

    if INDEX_PATH.exists():
        current_content = INDEX_PATH.read_text(encoding="utf-8")
        if current_content == new_content:
            # Ничего не изменилось
            return 0

    INDEX_PATH.write_text(new_content, encoding="utf-8")
    print(f"[generate_module_index] Updated {INDEX_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
