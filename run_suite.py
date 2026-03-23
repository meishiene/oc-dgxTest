from __future__ import annotations

import argparse
from pathlib import Path

from excel_webtest.excel_loader import load_cases
from excel_webtest.executor import run_suite
from excel_webtest.reporting import write_reports


def main() -> None:
    parser = argparse.ArgumentParser(description="Excel-driven Playwright runner")
    parser.add_argument("--excel", default="data/cases.xlsx", help="Excel 用例文件路径")
    parser.add_argument("--output-root", default="artifacts/runs", help="报告输出目录")
    parser.add_argument("--headed", action="store_true", help="显示浏览器窗口")
    parser.add_argument("--slow-mo", type=int, default=0, help="每个 Playwright 动作的慢放毫秒数")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="只运行指定 case_id，可重复传入")
    args = parser.parse_args()

    excel_path = Path(args.excel)
    if not excel_path.exists():
        raise SystemExit(f"Excel 文件不存在: {excel_path}")

    cases = load_cases(excel_path)
    suite = run_suite(
        cases=cases,
        excel_path=str(excel_path),
        output_root=args.output_root,
        headed=args.headed,
        slow_mo=args.slow_mo,
        case_ids=set(args.case_ids or []),
    )
    report_paths = write_reports(suite)

    print("\n=== Run Summary ===")
    print(f"Run ID: {suite.run_id}")
    print(f"Total : {suite.total}")
    print(f"Passed: {suite.passed}")
    print(f"Failed: {suite.failed}")
    print("\n=== Artifacts ===")
    for key, value in report_paths.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
