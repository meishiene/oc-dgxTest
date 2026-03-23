from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Browser, Error as PlaywrightError, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from .keywords import capture_actual, expected_value, perform_step
from .models import Case, CaseResult, Step, StepResult, SuiteResult


class Recorder:
    def __init__(self) -> None:
        self.console_errors: list[str] = []
        self.page_errors: list[str] = []
        self.request_failures: list[str] = []

    def bind(self, page: Page) -> None:
        page.on("console", self._on_console)
        page.on("pageerror", self._on_page_error)
        page.on("requestfailed", self._on_request_failed)

    def _on_console(self, message) -> None:
        if message.type == "error":
            self.console_errors.append(message.text)

    def _on_page_error(self, error: Exception) -> None:
        self.page_errors.append(str(error))

    def _on_request_failed(self, request) -> None:
        failure = request.failure
        if isinstance(failure, dict):
            reason = failure.get("errorText", "unknown")
        elif isinstance(failure, str):
            reason = failure
        elif failure:
            reason = str(failure)
        else:
            reason = "unknown"
        self.request_failures.append(f"{request.method} {request.url} :: {reason}")


def run_suite(
    cases: list[Case],
    excel_path: str,
    output_root: str,
    headed: bool = False,
    slow_mo: int = 0,
    case_ids: set[str] | None = None,
) -> SuiteResult:
    enabled_cases = [case for case in cases if case.enabled]
    if case_ids:
        enabled_cases = [case for case in enabled_cases if case.case_id in case_ids]

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(output_root).expanduser().resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    case_results: list[CaseResult] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed, slow_mo=slow_mo)
        try:
            for index, case in enumerate(enabled_cases, start=1):
                print(f"[{index}/{len(enabled_cases)}] {case.case_id} - {case.title}")
                case_results.append(_run_case(browser, case, run_dir))
        finally:
            browser.close()

    return SuiteResult(
        run_id=run_id,
        generated_at=_now(),
        excel_path=str(Path(excel_path).resolve()),
        run_dir=str(run_dir),
        cases=case_results,
    )


def _run_case(browser: Browser, case: Case, run_dir: Path) -> CaseResult:
    case_dir = run_dir / case.case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    started_at = _now()
    current_url = ""
    screenshot_path = ""
    trace_path = str(case_dir / "trace.zip")
    video_path = ""
    step_results: list[StepResult] = []
    recorder = Recorder()
    bug: dict | None = None

    context = browser.new_context(
        ignore_https_errors=True,
        viewport={"width": 1440, "height": 900},
        record_video_dir=str(case_dir / "video"),
        record_video_size={"width": 1440, "height": 900},
    )
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    recorder.bind(page)
    video = page.video

    try:
        for step in case.steps:
            effective_step = step
            if step.action.strip().lower() == "goto" and not step.value and case.start_url:
                effective_step = replace(step, value=case.start_url)

            step_started = _now()
            try:
                output = perform_step(page, effective_step, case_dir, recorder)
                if output.get("screenshot_path"):
                    screenshot_path = output["screenshot_path"]
                step_results.append(
                    StepResult(
                        step_no=effective_step.step_no,
                        action=effective_step.action,
                        status="passed",
                        started_at=step_started,
                        ended_at=_now(),
                        locator=effective_step.locator,
                        value=effective_step.value,
                        description=effective_step.description,
                    )
                )
            except Exception as error:
                current_url = page.url
                failure_shot = case_dir / f"failure-step-{effective_step.step_no:02d}.png"
                try:
                    page.screenshot(path=str(failure_shot), full_page=True)
                    screenshot_path = str(failure_shot)
                except PlaywrightError:
                    screenshot_path = screenshot_path or ""

                step_results.append(
                    StepResult(
                        step_no=effective_step.step_no,
                        action=effective_step.action,
                        status="failed",
                        started_at=step_started,
                        ended_at=_now(),
                        locator=effective_step.locator,
                        value=effective_step.value,
                        description=effective_step.description,
                        error_message=str(error),
                    )
                )
                bug = _build_bug(case, effective_step, error, page, recorder, screenshot_path, trace_path, video_path)
                raise

        current_url = page.url
        if not screenshot_path:
            final_shot = case_dir / "final.png"
            page.screenshot(path=str(final_shot), full_page=True)
            screenshot_path = str(final_shot)
    except Exception:
        status = "failed"
    else:
        status = "passed"
    finally:
        current_url = current_url or page.url
        try:
            context.tracing.stop(path=trace_path)
        except PlaywrightError:
            pass
        try:
            context.close()
        finally:
            if video is not None:
                try:
                    video_path = video.path()
                except PlaywrightError:
                    video_path = ""

    if bug is not None:
        bug["trace_path"] = trace_path
        bug["video_path"] = video_path

    return CaseResult(
        case_id=case.case_id,
        title=case.title,
        status=status,
        started_at=started_at,
        ended_at=_now(),
        current_url=current_url,
        steps=step_results,
        screenshot_path=screenshot_path,
        trace_path=trace_path,
        video_path=video_path,
        console_errors=recorder.console_errors,
        page_errors=recorder.page_errors,
        request_failures=recorder.request_failures,
        bug=bug,
    )


def _build_bug(
    case: Case,
    step: Step,
    error: Exception,
    page: Page,
    recorder: Recorder,
    screenshot_path: str,
    trace_path: str,
    video_path: str,
) -> dict:
    error_type = _classify_error(error)
    return {
        "bug_id": f"{case.case_id}-S{step.step_no:02d}",
        "case_id": case.case_id,
        "case_title": case.title,
        "failed_step_no": step.step_no,
        "failed_action": step.action,
        "failed_description": step.description,
        "url": page.url,
        "locator": step.locator,
        "expected": expected_value(step),
        "actual": capture_actual(page, step, recorder),
        "error_type": error_type,
        "error_message": str(error),
        "screenshot_path": screenshot_path,
        "trace_path": trace_path,
        "video_path": video_path,
        "console_errors": recorder.console_errors,
        "page_errors": recorder.page_errors,
        "request_failures": recorder.request_failures,
        "repro_steps": [
            f"{item.step_no}. {item.action} | locator={item.locator} | value={item.value}"
            for item in case.steps[: step.step_no]
        ],
        "handoff_summary": (
            f"用例 {case.case_id} 在第 {step.step_no} 步失败。"
            f"动作={step.action}，locator={step.locator or '-'}，expected={expected_value(step)}。"
        ),
    }


def _classify_error(error: Exception) -> str:
    if isinstance(error, AssertionError):
        return "assertion_failure"
    if isinstance(error, PlaywrightTimeoutError):
        return "timeout"
    if isinstance(error, PlaywrightError):
        return "playwright_error"
    return error.__class__.__name__


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
