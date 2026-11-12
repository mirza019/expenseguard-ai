# Siemens Energy AI & Context Engineer — implementation evidence

This document maps the independently built **FinContext AI** demonstration to the requested
AI and context-engineering capabilities. It is interview evidence, not product
branding and not a claim that this repository is a Siemens Energy system or deployment.

## Capability map

| Implemented capability | Financial context-engineering relevance | Main implementation | Verification and demonstration |
|---|---|---|---|
| Governed context registry | Definitions have versions, effective dates, owners, precedence, approval state and conflict detection. Extracted content does not become authoritative automatically. | `app/services/context_registry.py`, `app/ui/context_registry.py` | `tests/unit/test_context_registry.py`; create conflicting metric definitions, approve one, and resolve the applicable historical version. |
| Deterministic financial model | Financial totals, budget variance and anomaly checks remain code-calculated rather than LLM-generated. | `app/database/duckdb_service.py`, `app/tools/`, `app/services/planning.py` | Unit and integration reconciliation tests; trace a dashboard amount back to source rows. |
| Monthly review workflow | New data can drive a bounded variance investigation, observed cost-driver ranking, validation trace and human-review state without a chat prompt. | `app/workflows/monthly_close.py`, `app/ui/workflows.py` | `tests/unit/test_monthly_close.py`; run Monthly financial review from Agent Workflows and inspect the execution trace. |
| CSV/XLSX ingestion and profiling | Handles financial exports, aliases, validation, size limits and lineage while exposing invalid records. | `app/services/ingestion.py`, `app/ui/upload.py` | `tests/unit/test_ingestion.py`, `tests/unit/test_edge_cases.py`; load the fixed-seed 60,000-row workbook and inspect validation results. |
| Policy PDF context | Text/layout extraction retains document, version, section and page evidence; users can preview and download the original source. | `app/rag/`, `app/services/policy_rag.py`, `app/ui/knowledge_base.py` | `tests/integration/test_policy_intelligence.py`; ask which historical rule applied and open its cited PDF page. |
| Retrieval router and hybrid search | Numerical questions use controlled SQL/tools; knowledge questions use BM25, dense retrieval, RRF, metadata applicability filtering and optional reranking. | `app/rag/index.py`, `app/rag/answers.py`, `app/rag/compliance.py` | Run `scripts/evaluate_rag.py`; compare measured retrieval profiles and inspect failed questions in the Evaluation tab. |
| Bounded local agents | A supervisor selects allowlisted deterministic tools, validates evidence, limits retries and falls back safely when Ollama is unavailable. | `app/agents/graph.py`, `app/agents/finance_agent.py`, `app/prompts/` | `tests/unit/test_agent.py`, `tests/integration/test_workflow.py`; run a focused duplicate-payment request and inspect tool evidence. |
| Human-governed reporting | Findings and policy citations flow into validated ReportLab output; consequential interpretation stays awaiting review. | `app/services/reporting.py`, `app/reports/`, `app/ui/report_panel.py` | `tests/unit/test_pdf_generator.py`, `tests/integration/test_report_workflow.py`; compare the PDF KPI table with the dashboard. |
| Reproducible evaluation data | Fixed-seed financial history includes controlled duplicates, missing data, overruns, policy versions and separate ground truth. | `app/rag/datasets.py`, `scripts/`, `data/synthetic/ground_truth/` | Rebuild data, run retrieval/agent tests, and explain measured failures rather than presenting invented scores. |
| Responsible local operation | Read-only analytics, prompt-injection treatment, evidence abstention, audit traces and deterministic operation without a paid API. | `app/security/`, `app/agents/`, `start.sh` | Security and edge-case tests; stop Ollama and demonstrate that deterministic analytics still work. |

## Suggested interview demonstration

1. Start the app with `./start.sh` and load the fictional financial sample.
2. Show schema validation and source lineage in **Data & Context**.
3. Add or inspect a versioned policy PDF and open the cited page.
4. Run **Monthly financial review** and explain why category movements are observed contributors, not invented causes.
5. Run a focused expense-audit question and inspect its allowlisted tool trace.
6. Open the management report and reconcile one amount from source data through calculation to PDF.
7. Show the retrieval benchmark, including a failure case and a concrete improvement hypothesis.

## Explicit limitations

This local demonstration does not claim production ERP/SAP/Snowflake connectivity, enterprise SSO,
SharePoint ingestion, payment execution, certified audit assurance, OCR of scanned documents, or a
durable distributed scheduler. Enterprise adapters are architectural extension points only. The
included lexical reranker is not a production cross-encoder. Financial and policy conclusions require
human review before consequential use.
