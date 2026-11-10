# Testing and verification

## Commands

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov --cov-report=term-missing --cov-report=xml
```

## Coverage scope

Coverage includes services, tools, agents, the DuckDB adapter and reporting models/renderers/templates. Streamlit rendering and synthetic
generation are tested but excluded from the business-logic coverage denominator. An 80% minimum
is enforced in `pyproject.toml`. Coverage is a regression aid, not evidence of real-world fraud
accuracy or production readiness.

## Test strategy

- Ingestion: CSV/XLSX, unchanged IDs/strings, empty, invalid, oversized and expanded workbook limits.
- Validation: schema, malformed/missing values, currencies, monetary precision, source preservation.
- Duplicates: injected exact and possible groups, evidence, invalid configuration, no-match case.
- Budgets: repeated allocation counted once, conflicts, zero-budget percentages, injected overrun.
- Anomalies: known large expense, threshold evidence, small-cohort handling and multiplier bounds.
- Missing data: affected rows, exclusions and typed rules.
- SQL: department/category/month totals reconcile; unknown query names rejected.
- Agent: dynamic selection, evidence inspection, finish, invalid references, repeated actions, retries,
  unavailable model, safe errors, tool failure, result/number/reference validation.
- Ollama adapter: mocked HTTP/schema responses, malformed and oversized responses, loopback config.
- Integration: upload → validation → four-tool graph → SQL reconciliation → JSON/Markdown export.
- UI: Streamlit AppTest loads the sample and runs a complete deterministic audit without exceptions.

All tests run without paid APIs, network model services or a GPU. CI installs dependencies from the
package index but test execution itself requires no external service.

## Measured local result

Linux, Python 3.12.14: **111 tests passed; 97.72% statement coverage of 1,010 core/reporting
statements** after the PDF reporting extension. Three Node frontend tests passed. Ruff, formatting,
shell syntax, pinned dependency/configuration checks and pip consistency checks passed. Coverage now
includes report models, chart rendering, PDF composition and policy validation as well as the existing
financial/agent modules. It is not a claim of complete branch coverage or production audit accuracy.

The actual `./start.sh` installed/reused the pinned reporting dependencies and launched Streamlit;
the HTTP health endpoint returned `ok`. A4 PDF pages were rendered using PyMuPDF and inspected, with
automated text bounds/overlap checks, readable extraction and long-table pagination tests.

## CI

GitHub Actions tests Python 3.11 and 3.12, installs exact pinned dependencies, runs Ruff/formatting,
pytest with coverage, enforces the threshold, and uploads XML. It also checks startup shell syntax, imports/configuration, frontend tests and the fictional Pages report build. Pushes to main, feature/** and docs/**
and PRs targeting main trigger it. Main is never automatically merged or deployed.

## Manual acceptance still required

- Real Ollama/Qwen3 inference, a multi-GB model pull, installed quantization and useful tool selection.
- Apple Silicon installation and interactive latency/memory usage on the target Mac.
- Real browser upload/download interactions beyond Streamlit’s simulated UI tests.
- Operational security and data policies before any production use.

No screenshots are claimed because no real browser capture has been made. Windows PowerShell startup is supplied but was not executed here.

## Setup and agent regression tests

Model checks, downloads/progress/interruptions, post-download verification and ChatOllama structured
inference are mocked. Importing modules never pulls weights. Streamlit tests cover ready/missing/
unavailable models, successful setup, failed setup and continued deterministic auditing. LangChain
StructuredTool inputs reject arbitrary fields. Setup-script tests use a fake interpreter subprocess
and invoke the real shell script from a different working directory containing spaces.

Additional commands:

```bash
bash -n start.sh
python scripts/check_environment.py
python -c "import app.main; import app.agents.graph; import app.services.model_manager"
node --check site/app.mjs
node --test tests/frontend/report.test.mjs
python scripts/build_pages_demo.py
```

## PDF reporting checks

The suite covers verified monetary totals, period changes, source-row mapping and cross-period ID
revalidation, chart/table reconciliation, financial finding references, policy citation fabrication,
version/effective-date selection, related guidance versus exceptions, invalid numerics, empty findings,
long Unicode descriptions, large tables, actual PDF rendering, download/cache behavior, optional
LangGraph report actions and CSV-to-audit-to-PDF integration. No model/API is needed.

```bash
python -m pytest tests/unit/test_pdf_generator.py tests/unit/test_report_validation.py \
  tests/unit/test_policy_rag.py tests/integration/test_report_workflow.py
python scripts/generate_sample_report.py
```

The example is generated solely from fictional data and policy text. Its 11 pages (about 175 KB)
were visually inspected for chart labels, table continuation, findings and policy references.
