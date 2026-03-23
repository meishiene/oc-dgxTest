from __future__ import annotations

import html
import json
from pathlib import Path

from .models import CaseResult, SuiteResult


def write_reports(suite: SuiteResult) -> dict[str, str]:
    run_dir = Path(suite.run_dir)
    summary_path = run_dir / "summary.json"
    bugs_json_path = run_dir / "bugs.json"
    bugs_md_path = run_dir / "bugs.md"
    report_html_path = run_dir / "report.html"

    summary_path.write_text(
        json.dumps(
            {
                **suite.to_summary(),
                "cases": [_case_to_dict(case) for case in suite.cases],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    bugs_json_path.write_text(
        json.dumps(
            {
                "run_id": suite.run_id,
                "generated_at": suite.generated_at,
                "bugs": [case.bug for case in suite.cases if case.bug],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    bugs_md_path.write_text(_build_bugs_markdown(suite), encoding="utf-8")
    report_html_path.write_text(_build_html_report(suite), encoding="utf-8")

    return {
        "summary_json": str(summary_path),
        "bugs_json": str(bugs_json_path),
        "bugs_md": str(bugs_md_path),
        "report_html": str(report_html_path),
    }


def _case_to_dict(case: CaseResult) -> dict:
    return {
        "case_id": case.case_id,
        "title": case.title,
        "status": case.status,
        "started_at": case.started_at,
        "ended_at": case.ended_at,
        "current_url": case.current_url,
        "screenshot_path": case.screenshot_path,
        "trace_path": case.trace_path,
        "video_path": case.video_path,
        "console_errors": case.console_errors,
        "page_errors": case.page_errors,
        "request_failures": case.request_failures,
        "steps": [
            {
                "step_no": step.step_no,
                "action": step.action,
                "status": step.status,
                "locator": step.locator,
                "value": step.value,
                "description": step.description,
                "started_at": step.started_at,
                "ended_at": step.ended_at,
                "error_message": step.error_message,
            }
            for step in case.steps
        ],
        "bug": case.bug,
    }


def _build_bugs_markdown(suite: SuiteResult) -> str:
    lines = [
        f"# DGX 测试 Bug 单 - {suite.run_id}",
        "",
        f"- 生成时间: {suite.generated_at}",
        f"- 总用例: {suite.total}",
        f"- 通过: {suite.passed}",
        f"- 失败: {suite.failed}",
        "",
    ]
    bugs = [case.bug for case in suite.cases if case.bug]
    if not bugs:
        lines.append("本次运行没有发现失败用例。")
        lines.append("")
        return "\n".join(lines)

    for bug in bugs:
        lines.extend(
            [
                f"## {bug['bug_id']} - {bug['case_title']}",
                "",
                f"- 用例ID: {bug['case_id']}",
                f"- 失败步骤: {bug['failed_step_no']}",
                f"- 动作: {bug['failed_action']}",
                f"- 页面URL: {bug['url']}",
                f"- 定位器: `{bug['locator'] or '-'}`",
                f"- 预期: {bug['expected']}",
                f"- 实际: {bug['actual'] or '-'}",
                f"- 错误类型: {bug['error_type']}",
                f"- 错误信息: {bug['error_message']}",
                f"- 截图: `{bug['screenshot_path'] or '-'}`",
                f"- Trace: `{bug['trace_path'] or '-'}`",
                f"- Video: `{bug['video_path'] or '-'}`",
                "",
                "### 复现步骤",
                "",
            ]
        )
        for step in bug["repro_steps"]:
            lines.append(f"- {step}")
        if bug["console_errors"]:
            lines.extend(["", "### Console Errors", ""])
            for item in bug["console_errors"]:
                lines.append(f"- {item}")
        if bug["page_errors"]:
            lines.extend(["", "### Page Errors", ""])
            for item in bug["page_errors"]:
                lines.append(f"- {item}")
        if bug["request_failures"]:
            lines.extend(["", "### Request Failures", ""])
            for item in bug["request_failures"]:
                lines.append(f"- {item}")
        lines.extend(["", "### 交接摘要", "", bug["handoff_summary"], ""])
    return "\n".join(lines)


def _build_html_report(suite: SuiteResult) -> str:
    rows = []
    for case in suite.cases:
        rows.append(
            "<tr>"
            f"<td>{html.escape(case.case_id)}</td>"
            f"<td>{html.escape(case.title)}</td>"
            f"<td class='{case.status}'>{html.escape(case.status)}</td>"
            f"<td>{html.escape(case.current_url)}</td>"
            f"<td>{_link(case.screenshot_path, suite.run_dir, 'screenshot')}</td>"
            f"<td>{_link(case.trace_path, suite.run_dir, 'trace')}</td>"
            f"<td>{_link(case.video_path, suite.run_dir, 'video')}</td>"
            "</tr>"
        )

    details = []
    for case in suite.cases:
        details.append(f"<h2>{html.escape(case.case_id)} - {html.escape(case.title)}</h2>")
        details.append("<ul>")
        details.append(f"<li>Status: <strong class='{case.status}'>{html.escape(case.status)}</strong></li>")
        details.append(f"<li>Started: {html.escape(case.started_at)}</li>")
        details.append(f"<li>Ended: {html.escape(case.ended_at)}</li>")
        details.append(f"<li>URL: {html.escape(case.current_url)}</li>")
        details.append("</ul>")
        details.append("<table><thead><tr><th>Step</th><th>Action</th><th>Status</th><th>Locator</th><th>Value</th><th>Error</th></tr></thead><tbody>")
        for step in case.steps:
            details.append(
                "<tr>"
                f"<td>{step.step_no}</td>"
                f"<td>{html.escape(step.action)}</td>"
                f"<td class='{step.status}'>{html.escape(step.status)}</td>"
                f"<td>{html.escape(step.locator)}</td>"
                f"<td>{html.escape(step.value)}</td>"
                f"<td>{html.escape(step.error_message)}</td>"
                "</tr>"
            )
        details.append("</tbody></table>")
        if case.bug:
            details.append("<div class='bug-box'>")
            details.append(f"<strong>Bug ID:</strong> {html.escape(case.bug['bug_id'])}<br>")
            details.append(f"<strong>Expected:</strong> {html.escape(case.bug['expected'])}<br>")
            details.append(f"<strong>Actual:</strong> {html.escape(case.bug['actual'] or '-') }<br>")
            details.append(f"<strong>Error:</strong> {html.escape(case.bug['error_message'])}")
            details.append("</div>")

    return f"""<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='utf-8'>
  <title>DGX Test Report - {html.escape(suite.run_id)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 24px; color: #1f2328; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #d0d7de; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f6f8fa; }}
    .passed {{ color: #1a7f37; font-weight: 700; }}
    .failed {{ color: #cf222e; font-weight: 700; }}
    .bug-box {{ padding: 12px; background: #fff8c5; border: 1px solid #d4a72c; margin-bottom: 24px; }}
    .summary {{ display: flex; gap: 24px; margin-bottom: 20px; }}
    .summary div {{ padding: 12px 16px; background: #f6f8fa; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>DGX 测试报告</h1>
  <div class='summary'>
    <div>Run ID: <strong>{html.escape(suite.run_id)}</strong></div>
    <div>Total: <strong>{suite.total}</strong></div>
    <div>Passed: <strong class='passed'>{suite.passed}</strong></div>
    <div>Failed: <strong class='failed'>{suite.failed}</strong></div>
  </div>
  <table>
    <thead>
      <tr><th>Case ID</th><th>Title</th><th>Status</th><th>Current URL</th><th>Screenshot</th><th>Trace</th><th>Video</th></tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  {''.join(details)}
</body>
</html>
"""


def _link(path_text: str, run_dir: str, label: str) -> str:
    if not path_text:
        return "-"
    path = Path(path_text)
    try:
        href = path.relative_to(run_dir).as_posix()
    except ValueError:
        href = path_text
    return f"<a href='{html.escape(href)}'>{html.escape(label)}</a>"
