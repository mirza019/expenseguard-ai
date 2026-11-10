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

Linux, Python 3.12: **131 tests passed; 96.28% statement coverage** of 1,857 selected core/reporting/
RAG/evaluation statements (69 uncovered). The full command ran in 134.98 seconds. Coverage includes
services, tools, agents, DuckDB, reports, RAG and evaluation; UI and generation are additionally tested
outside that denominator. This measures regression coverage, not financial fraud detection accuracy.

Real Chromium inspection captured all eight tabs at 1440×1000 and Overview at 390×844 after loading
2,400 transactions, indexing policies and running the audit. No page errors or horizontal document
overflow were observed. Screenshots are in `docs/screenshots`. Streamlit AppTest independently covers
loading, model setup, audit, PDF download controls and session-cache behavior. PDF tests render actual
A4 pages and inspect text bounds/pagination. See the release engineering report for final CI status.

## CI

GitHub Actions tests Python 3.11 and 3.12, installs exact pinned dependencies, runs Ruff/formatting,
pytest with coverage, enforces the threshold, and uploads XML. It also checks startup shell syntax, imports/configuration, frontend tests and the fictional Pages report build. Pushes to main, feature/** and docs/**
and PRs targeting main trigger it. Main is never automatically merged or deployed.

## Manual acceptance still required

- Real Ollama/Qwen3 inference, a multi-GB model pull, installed quantization and useful tool selection.
- Apple Silicon installation and interactive latency/memory usage on the target Mac.
- Additional real-browser upload formats and every platform-specific file picker.
- Operational security and data policies before any production use.

Screenshots document actual Chromium rendering, not Mac/Safari behavior. Windows PowerShell startup is supplied but was not executed here.

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


## RAG and planning regressions

`tests/unit/test_rag_pipeline.py` checks reproducible PDFs/CSV/XLSX/questions, section/page boundaries,
parent context, exceptions, scope/version filters, duplicates/reindexing, corrupt metadata, index
replacement safety, BM25 avoiding embeddings, citation validation, metric arithmetic and unavailable
or mocked live models. Unknown emergency approval and unsupported approver roles require more evidence.
`test_planning.py` independently verifies scenario cents, run-rate assumptions and category contributions.
`tests/integration/test_policy_intelligence.py` covers October scope → four-tool LangGraph → historical
policy controls → verified PDF, source failure and the integrated Streamlit demo.

The manual-only `rag-benchmark.yml` runs a full no-model benchmark. Optional real MiniLM evaluation was
run locally, separately from lightweight CI. No ordinary test downloads embeddings or Qwen weights.
