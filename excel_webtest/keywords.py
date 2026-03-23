from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from .models import Step


LOCATOR_ACTIONS = {
    "click",
    "fill",
    "press",
    "hover",
    "select_option",
    "assert_visible",
    "assert_hidden",
    "assert_text_contains",
    "assert_count_gte",
    "wait_for_selector",
}


def perform_step(page: Page, step: Step, artifact_dir: Path, recorder) -> dict[str, str]:
    action = step.action.strip().lower()
    if not action:
        raise ValueError("step.action 不能为空")

    if action == "goto":
        target_url = step.value.strip() or page.url
        if not target_url:
            raise ValueError("goto 需要 value 填 URL")
        page.goto(target_url, wait_until="domcontentloaded", timeout=step.timeout_ms)
        return {}

    if action == "wait_for_load_state":
        state = step.value.strip() or "load"
        page.wait_for_load_state(state=state, timeout=step.timeout_ms)
        return {}

    if action == "wait_for_timeout":
        page.wait_for_timeout(_to_int(step.value, step.timeout_ms))
        return {}

    if action == "assert_title_contains":
        title = page.title()
        _assert_contains(step.value, title, f"标题未包含预期文本: {step.value}")
        return {}

    if action == "assert_url_contains":
        current_url = page.url
        _assert_contains(step.value, current_url, f"URL 未包含预期文本: {step.value}")
        return {}

    if action == "assert_console_errors_lte":
        actual_count = len(recorder.console_errors)
        max_count = _to_int(step.value, 0)
        if actual_count > max_count:
            raise AssertionError(f"console error 数量过多，expected<={max_count}, actual={actual_count}")
        return {}

    if action == "assert_page_errors_lte":
        actual_count = len(recorder.page_errors)
        max_count = _to_int(step.value, 0)
        if actual_count > max_count:
            raise AssertionError(f"page error 数量过多，expected<={max_count}, actual={actual_count}")
        return {}

    if action == "assert_request_failures_lte":
        actual_count = len(recorder.request_failures)
        max_count = _to_int(step.value, 0)
        if actual_count > max_count:
            raise AssertionError(f"request failure 数量过多，expected<={max_count}, actual={actual_count}")
        return {}

    if action == "screenshot":
        label = _safe_name(step.value or f"step-{step.step_no:02d}")
        screenshot_path = artifact_dir / "screenshots" / f"{label}.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path), full_page=True)
        return {"screenshot_path": str(screenshot_path)}

    if action in LOCATOR_ACTIONS:
        locator = page.locator(step.locator)
        first_locator = locator.first

        if action == "wait_for_selector":
            state = step.value.strip() or "visible"
            locator.wait_for(state=state, timeout=step.timeout_ms)
            return {}

        if action == "click":
            first_locator.click(timeout=step.timeout_ms)
            return {}

        if action == "fill":
            first_locator.fill(step.value, timeout=step.timeout_ms)
            return {}

        if action == "press":
            first_locator.press(step.value, timeout=step.timeout_ms)
            return {}

        if action == "hover":
            first_locator.hover(timeout=step.timeout_ms)
            return {}

        if action == "select_option":
            first_locator.select_option(step.value, timeout=step.timeout_ms)
            return {}

        if action == "assert_visible":
            if not first_locator.is_visible(timeout=step.timeout_ms):
                raise AssertionError(f"元素不可见: {step.locator}")
            return {}

        if action == "assert_hidden":
            if first_locator.is_visible(timeout=step.timeout_ms):
                raise AssertionError(f"元素仍然可见: {step.locator}")
            return {}

        if action == "assert_text_contains":
            actual_text = (first_locator.inner_text(timeout=step.timeout_ms) or "").strip()
            _assert_contains(step.value, actual_text, f"元素文本未包含预期内容: {step.value}")
            return {}

        if action == "assert_count_gte":
            actual_count = locator.count()
            min_count = _to_int(step.value, 1)
            if actual_count < min_count:
                raise AssertionError(f"元素数量不足，expected>={min_count}, actual={actual_count}, locator={step.locator}")
            return {}

    raise ValueError(f"暂不支持的 action: {step.action}")


def capture_actual(page: Page, step: Step, recorder) -> str:
    action = step.action.strip().lower()
    if action == "assert_title_contains":
        return page.title()
    if action == "assert_url_contains":
        return page.url
    if action == "assert_console_errors_lte":
        return str(len(recorder.console_errors))
    if action == "assert_page_errors_lte":
        return str(len(recorder.page_errors))
    if action == "assert_request_failures_lte":
        return str(len(recorder.request_failures))
    if action == "assert_visible" and step.locator:
        locator = page.locator(step.locator)
        return f"visible={locator.first.is_visible()} count={locator.count()}"
    if action == "assert_hidden" and step.locator:
        locator = page.locator(step.locator)
        return f"visible={locator.first.is_visible()} count={locator.count()}"
    if action == "assert_text_contains" and step.locator:
        return (page.locator(step.locator).first.text_content(timeout=step.timeout_ms) or "").strip()
    if action == "assert_count_gte" and step.locator:
        return str(page.locator(step.locator).count())
    return ""


def expected_value(step: Step) -> str:
    action = step.action.strip().lower()
    if action == "assert_visible":
        return "visible"
    if action == "assert_hidden":
        return "hidden"
    if action == "assert_count_gte":
        return f">= {step.value}"
    if action.endswith("_lte"):
        return f"<= {step.value}"
    if action.startswith("assert_"):
        return step.value
    if action == "click":
        return "click succeeds"
    if action == "fill":
        return f"fill succeeds with value={step.value}"
    return step.value


def _assert_contains(expected: str, actual: str, message: str) -> None:
    if expected not in actual:
        raise AssertionError(f"{message}; actual={actual}")


def _to_int(value: str, default: int) -> int:
    text = str(value).strip()
    if not text:
        return default
    return int(float(text))


def _safe_name(value: str) -> str:
    keep = []
    for char in value:
        if char.isalnum() or char in {"-", "_"}:
            keep.append(char)
        else:
            keep.append("-")
    cleaned = "".join(keep).strip("-")
    return cleaned or "screenshot"
