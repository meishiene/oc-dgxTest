from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Step:
    case_id: str
    step_no: int
    action: str
    locator: str = ""
    value: str = ""
    timeout_ms: int = 5000
    description: str = ""


@dataclass(slots=True)
class Case:
    case_id: str
    title: str
    enabled: bool
    start_url: str
    tags: str = ""
    notes: str = ""
    steps: list[Step] = field(default_factory=list)


@dataclass(slots=True)
class StepResult:
    step_no: int
    action: str
    status: str
    started_at: str
    ended_at: str
    locator: str = ""
    value: str = ""
    description: str = ""
    error_message: str = ""


@dataclass(slots=True)
class CaseResult:
    case_id: str
    title: str
    status: str
    started_at: str
    ended_at: str
    current_url: str
    steps: list[StepResult] = field(default_factory=list)
    screenshot_path: str = ""
    trace_path: str = ""
    video_path: str = ""
    console_errors: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    request_failures: list[str] = field(default_factory=list)
    bug: dict[str, Any] | None = None


@dataclass(slots=True)
class SuiteResult:
    run_id: str
    generated_at: str
    excel_path: str
    run_dir: str
    cases: list[CaseResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def passed(self) -> int:
        return sum(1 for case in self.cases if case.status == "passed")

    @property
    def failed(self) -> int:
        return sum(1 for case in self.cases if case.status == "failed")

    def to_summary(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "excel_path": self.excel_path,
            "run_dir": self.run_dir,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
            },
        }
