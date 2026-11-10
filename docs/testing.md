# Testing and verification

## Commands

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov --cov-report=term-missing --cov-report=xml
```

## Coverage scope

Coverage includes services, tools, agents and the DuckDB adapter. Streamlit rendering and synthetic
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

Linux, Python 3.12.14: **75 tests passed; 100% statement coverage of 437 core statements** after
ChatOllama, model setup and startup integration. Three Node frontend tests also passed. Ruff and
formatting checks passed. This describes the tested revision; rerun after changes. Statement coverage
is not complete branch coverage or evidence of real-world fraud accuracy.

The actual `./start.sh` launched Streamlit successfully on loopback. Mock-interpreter tests exercise
first-run venv creation, repeated starts, missing dependencies, changed pins, installation failure,
unsupported Python and setup locking without installing anything or downloading models.

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
