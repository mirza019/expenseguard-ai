# FinContext AI

**Autonomous Financial Intelligence & Context Engineering Platform**

FinContext AI is a local-first financial intelligence platform that combines structured financial
analytics, governed business knowledge, hybrid retrieval, and autonomous AI workflows. It helps
finance teams turn fragmented financial data and documents into consistent calculations,
explainable investigations, and evidence-based management reports.

The application works without a chat question. A finance user can load a fictional or real-format
expense export, run the monthly financial review, review material variances, and retain human control
over context approval and final reporting. Optional local Qwen inference can guide bounded tool
selection; Python and DuckDB remain responsible for financial calculations.

> This is an open-source reference implementation using fictional data, not a certified audit,
> accounting, or payment system. Findings are investigation leads and require human review.

## Business value

| Problem | FinContext AI solution | Result |
|---|---|---|
| Budget and actual figures are repeated across spreadsheets | Validated normalization and declared allocation-grain reconciliation | Traceable actual, budget, variance, and completeness status |
| KPI and policy definitions change over time | Versioned context assets with scope, provenance, precedence, and approval | Workflows can distinguish drafts from approved definitions |
| Analysts manually search policy PDFs | Structure-aware PDF extraction, metadata filtering, BM25/dense hybrid retrieval, and citations | Applicable evidence remains inspectable by document, section, page, and version |
| Large deviations need explanation | A bounded monthly close workflow ranks departments and arithmetic contributors | Finance receives a review draft without fabricated causal claims |
| AI output can be difficult to verify | Allowlisted tools, deterministic validation, bounded retries, trace logs, and human approval | Model assistance cannot silently change financial data or invent calculations |

## Four workspaces

1. **Dashboard** — actual, represented budget, variance, trends, recent workflow status, and review state.
2. **Data & Context** — CSV/XLSX intake, validation, policy sources, and the governed context registry.
3. **Agent Workflows** — monthly financial review, reusable expense compliance audit, and optional Ask AI.
4. **Reports & Governance** — findings, PDF/JSON/CSV evidence, retrieval evaluation, and diagnostics.

## Implemented capabilities

- CSV and XLSX expense ingestion with immutable source representation, explicit normalization,
  row limits, ZIP expansion protection, exact cents, and quality evidence.
- Text-based PDF extraction with page provenance; scanned documents are rejected rather than
  presented as successfully extracted.
- DuckDB-backed aggregation and deterministic tools for budget reconciliation, duplicates,
  category outliers, and missing or invalid data.
- Versioned context registry with draft/approved states, effective dates, owners, hashes,
  precedence, and conflict detection.
- Monthly financial review and variance investigation with idempotency keys, reconciliation,
  materiality thresholds, observed contributors, limitations, and human-review status.
- Policy RAG with hierarchical chunks, source metadata, BM25 and dense retrieval profiles,
  reciprocal-rank fusion, citation checks, historical applicability, and evaluation fixtures.
- Bounded LangGraph orchestration with registered tools, structured decisions, retries,
  deterministic fallback, and evidence validation.
- Multipage ReportLab PDF reports using the same validated result objects as the application.
- Reproducible synthetic transactions and policy documents, automated tests, Ruff, and CI.

## Honest capability status

| Area | Status |
|---|---|
| Expense CSV/XLSX ingestion and audit | Implemented and tested |
| Text PDF policy extraction and hybrid retrieval | Implemented and tested |
| Governed context assets and approval | Implemented locally |
| Monthly variance workflow | Implemented for the normalized expense/budget model |
| Separate ERP actual/budget/forecast table ingestion | Planned |
| Spreadsheet glossary/notes extraction across arbitrary layouts | Experimental / partial |
| OCR for scanned PDFs | Flagged as requiring OCR; OCR is not bundled |
| Background scheduling and event worker | Planned; Streamlit does not run production schedules |
| RBAC, SSO, ERP writeback, Snowflake, SharePoint | Architectural adapters only; not implemented |

## Quick start

Requirements: macOS/Linux/Windows, Python 3.11 or 3.12, and approximately 2 GB free space.
Ollama is optional.

```bash
git clone https://github.com/mirza019/expenseguard-ai.git
cd expenseguard-ai
git switch develop
./start.sh
```

Open `http://127.0.0.1:8503`, choose **Data & Context**, and click **Try fictional sample**.
Port 8503 is the project default so it does not conflict with other local Streamlit applications.
Then open **Agent Workflows** and run **Monthly Financial Review & Variance Investigation**.

Manual setup:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app/main.py
```

Optional local AI:

```bash
ollama serve
ollama pull qwen3:4b-q4_K_M
```

FinContext AI still provides deterministic analytics when Ollama is unavailable. Startup never
silently downloads an LLM.

## Quality checks

```bash
pytest -q
ruff check app tests scripts
python scripts/evaluate_rag.py
```

Benchmark output is written from real evaluation runs; the repository does not invent scores.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Context engineering](docs/CONTEXT_ENGINEERING.md)
- [Retrieval engine](docs/RETRIEVAL_ENGINE.md)
- [Agent workflows](docs/AGENT_WORKFLOWS.md)
- [Financial analytics](docs/FINANCIAL_ANALYTICS.md)
- [Evaluation](docs/EVALUATION.md)
- [Security and Responsible AI](docs/SECURITY.md)
- [Fictional product demonstration](docs/DEMO.md)
- [Capability evidence and limitations](docs/CAPABILITY_EVIDENCE.md)

## Privacy and safety

- Local execution is the default; no paid API is required.
- Analytical tools are read-only and do not modify financial records.
- Uploaded sources are preserved separately from normalized analytical copies.
- Retrieved evidence must pass source and applicability checks before it reaches explanations.
- Context changes and final reports remain subject to explicit human review.
- Real financial files may contain sensitive information; operators remain responsible for local
  access controls, retention, backups, and legal obligations.

## License

See [LICENSE](LICENSE).
