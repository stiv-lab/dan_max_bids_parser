# path: tests/interfaces/test_harvest_source_cli.py
from __future__ import annotations

"""
Тесты для CLI-модуля harvest_source_cli.

Проверяем:
- успешный сценарий main(...);
- обработку ValueError (ожидаемая бизнес-ошибка);
- обработку неожиданного исключения.
"""

from typing import Any

import pytest

from dan_max_bids_parser.interfaces import harvest_source_cli


def test_main_success_calls_run_harvest_and_returns_zero(monkeypatch, capsys):
    """
    Успешный сценарий:
    - main() вызывает run_harvest с корректным source_code;
    - возвращает код 0;
    - печатает сообщение об успешном завершении.
    """

    called: dict[str, Any] = {}

    def fake_run_harvest(source_code: str) -> None:
        called["source_code"] = source_code

    monkeypatch.setattr(
        harvest_source_cli,
        "run_harvest",
        fake_run_harvest,
    )

    exit_code = harvest_source_cli.main(["--source-code", "ATI"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Harvesting finished for source_code='ATI'" in captured.out
    assert called.get("source_code") == "ATI"


def test_main_returns_one_on_value_error(monkeypatch, capsys):
    """
    При возникновении ValueError в run_harvest:
    - main() должен вернуть код 1;
    - напечатать сообщение с префиксом 'ERROR:'.
    """

    def fake_run_harvest(source_code: str) -> None:  # noqa: ARG001
        raise ValueError("Source with code='UNKNOWN' not found")

    monkeypatch.setattr(
        harvest_source_cli,
        "run_harvest",
        fake_run_harvest,
    )

    exit_code = harvest_source_cli.main(["--source-code", "UNKNOWN"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "ERROR: Source with code='UNKNOWN' not found" in captured.out


def test_main_returns_one_on_unexpected_exception(monkeypatch, capsys):
    """
    При неожиданном исключении (не ValueError):
    - main() должен вернуть код 1;
    - напечатать сообщение с префиксом 'UNEXPECTED ERROR:'.
    """

    def fake_run_harvest(source_code: str) -> None:  # noqa: ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr(
        harvest_source_cli,
        "run_harvest",
        fake_run_harvest,
    )

    exit_code = harvest_source_cli.main(["--source-code", "ATI"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "UNEXPECTED ERROR: boom" in captured.out
