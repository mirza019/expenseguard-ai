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

Linux, Python 3.12.14: **49 tests passed; 100% statement coverage of 356 core statements** at initial
full verification. Ruff and formatting checks passed. This number describes the tested revision;
rerun the commands after changes. Do not interpret statement coverage as complete branch coverage.

## CI

GitHub Actions tests Python 3.11 and 3.12, installs exact pinned dependencies, runs Ruff/formatting,
pytest with coverage, enforces the threshold, and uploads XML. Pushes to main, feature/** and docs/**
and PRs targeting main trigger it. Main is never automatically merged or deployed.

## Manual acceptance still required

- Real Ollama/Qwen3 inference, installed model quantization and useful tool selection.
- Apple Silicon installation and interactive latency/memory usage on the target Mac.
- Real browser upload/download interactions beyond Streamlit’s simulated UI tests.
- Operational security and data policies before any production use.

No screenshots are claimed because no real browser capture has been made.
