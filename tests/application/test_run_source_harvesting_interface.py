# path: tests/application/test_run_source_harvesting_interface.py
from dataclasses import dataclass

from dan_max_bids_parser.application.use_cases.harvest_source import (
    RunSourceHarvestingCommand,
    RunSourceHarvestingUseCase,
)


@dataclass
class DummyRunSourceHarvestingUseCase(RunSourceHarvestingUseCase):
    executed_with: list[str]

    def execute(self, command: RunSourceHarvestingCommand) -> None:
        self.executed_with.append(command.source_code)


def test_run_source_harvesting_use_case_interface():
    use_case = DummyRunSourceHarvestingUseCase(executed_with=[])
    cmd = RunSourceHarvestingCommand(source_code="ATI")

    use_case.execute(cmd)

    assert use_case.executed_with == ["ATI"]
