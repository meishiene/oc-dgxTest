# DGX Playwright + Python 自动化测试骨架

这是一个 **Excel 驱动** 的网页自动化测试脚手架，目标是：

- 用 `Excel` 管理测试用例
- 用 `Playwright + Python` 执行页面操作和断言
- 跑完后自动输出：
  - `report.html`：给人看的测试报告
  - `bugs.md`：可直接发给研发/测试群的 bug 单
  - `bugs.json`：给其他 AI 精准消费的结构化 bug 数据

当前默认目标站点：`https://dgx.xlook.ai/dgx/93e7ea32-0a24-4ad9-ad46-d3362e027ab7`

## 目录

```text
projects/dgx-playwright-python/
├── create_sample_excel.py
├── data/
├── excel_webtest/
│   ├── excel_loader.py
│   ├── executor.py
│   ├── keywords.py
│   ├── models.py
│   └── reporting.py
├── requirements.txt
└── run_suite.py
```

## 快速开始

```bash
cd /Users/xkool/.openclaw/workspace/projects/dgx-playwright-python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python create_sample_excel.py
python run_suite.py --excel data/cases.xlsx
```

如果想看浏览器执行过程：

```bash
python run_suite.py --excel data/cases.xlsx --headed --slow-mo 250
```

## Excel 约定

### `cases` sheet

- `case_id`：唯一标识
- `title`：用例标题
- `enabled`：是否执行，`1/0` 或 `true/false`
- `start_url`：起始 URL
- `tags`：标签，逗号分隔
- `notes`：备注

### `steps` sheet

- `case_id`：关联到 `cases.case_id`
- `step_no`：步骤序号
- `action`：动作名
- `locator`：Playwright locator
  - 例如：`text=Leaflet`
  - 或：`role=button[name='Next']`
- `value`：动作值 / 断言值
- `timeout_ms`：超时时间
- `description`：步骤说明

### 当前支持的动作

- `goto`
- `wait_for_load_state`
- `wait_for_timeout`
- `click`
- `fill`
- `press`
- `hover`
- `select_option`
- `assert_title_contains`
- `assert_url_contains`
- `assert_visible`
- `assert_hidden`
- `assert_text_contains`
- `assert_count_gte`
- `assert_page_errors_lte`
- `assert_console_errors_lte`
- `assert_request_failures_lte`
- `screenshot`

## 产物说明

每次运行都会生成一个新目录，例如：

```text
artifacts/runs/20260323-160000/
```

其中包含：

- `summary.json`：完整执行摘要
- `report.html`：测试报告
- `bugs.md`：文本版 bug 单
- `bugs.json`：结构化 bug 单
- `DGX-001/trace.zip`：Playwright trace
- `DGX-001/failure-step-03.png`：失败截图
- `DGX-001/video/`：录屏

## 给其他 AI 的最佳交接方式

优先把这两个文件丢给它：

- `artifacts/runs/<run_id>/bugs.json`
- `artifacts/runs/<run_id>/bugs.md`

因为 `bugs.json` 里已经带了这些关键字段：

- `case_id`
- `failed_step_no`
- `failed_action`
- `url`
- `locator`
- `expected`
- `actual`
- `error_type`
- `error_message`
- `screenshot_path`
- `trace_path`
- `console_errors`
- `page_errors`
- `request_failures`
- `repro_steps`

这比只发一句“某页面挂了”更适合让 AI 精准定位问题。

## 下一步建议

你现在最适合做的是：

1. 先运行默认 smoke 用例，确认环境通了
2. 再按页面实际交互，把业务步骤逐条补到 Excel
3. 一旦发现稳定的关键元素，优先用更稳的 locator
4. 后续如果你愿意，可以继续加：
   - CSV/Excel 批量数据驱动
   - API 预置测试数据
   - 更细的 bug 分类
   - Jira/飞书 bug 单自动生成
