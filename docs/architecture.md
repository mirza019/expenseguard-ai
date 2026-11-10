# Architecture and operational handover

## Components

`app/main.py` composes upload, dashboard, audit, agent and reporting panels. Services perform ingestion,
validation, tool registration and reporting. Tools return Pydantic results. The database adapter opens
and closes one in-memory DuckDB connection per fixed aggregate query; it never accepts arbitrary SQL.
LangGraph carries per-run state without shared checkpoints. Settings use `.env` for local Ollama. The model manager uses the Ollama Python SDK, and inference uses LangChain ChatOllama.

```mermaid
flowchart TD
    Upload --> Ingestion
    Ingestion --> Original[Original frame]
    Ingestion --> Validation
    Validation --> Clean[Cleaned frame + exclusions + issues]
    Clean --> Tools
    Clean --> DuckDB
    Tools --> Evidence[Validated findings]
    Evidence --> Report
    DuckDB --> Dashboard
    Report --> Dashboard
    Report --> ValidateReport[Report validation]
    Policies[Policy PDFs] --> RAG[PyMuPDF hierarchical chunks + metadata + FAISS/BM25/RRF]
    RAG --> Citations[Verified policy citations]
    Citations --> ValidateReport
    ValidateReport --> PDF[ReportLab PDF]
    PDF --> Downloads
    Report --> Downloads
```

## Data ownership and transformations

The user owns uploaded data. No original uploaded financial data is written to disk. The launcher creates ignored environment/config/cache directories and uses the intentional fictional fixture. The normalized copy trims strings,
uppercases currency, parses exact cents and dates, derives months, and marks financial eligibility.
`source_row` refers to CSV/worksheet row numbers with row 1 reserved for headers. Duplicate IDs are
not removed; row numbers are the stable evidence references. XLSX ingestion reads the first sheet.
Files with repeated headers or nonstandard schemas should be corrected before loading.

Budget allocation grain is month/department/cost center. Repeated equal values represent one budget,
not multiple allocations. Conflicts are surfaced and aggregate variance is withheld. Financial
actuals include all payment statuses and duplicate candidates until review. Totals describe the
uploaded file, not necessarily an entire organization.

## State lifecycle

A successful load replaces the session dataset and clears previous audit outputs. Failed loads retain
the preceding dataset with an explicit warning. Reruns retain session state; browser-session loss or
process restart removes it. Report exports use memory, not shared temporary paths. No cross-user
persistent connection or cache stores financial records.

## Suggested ownership and runbook

For this solo project, the developer maintains source and tests; an expense reviewer investigates
flags; a budget owner resolves allocation conflicts. These are proposed responsibilities, not claims
of actual organizational deployment.

1. Install pinned dependencies in a virtual environment.
2. Run lint, tests and coverage before changes.
3. Regenerate fictional fixtures only with a recorded seed and review the manifest.
4. Start Streamlit and load a small sample before real authorized uploads.
5. Verify exclusions, currency and budget scope before interpreting totals.
6. Check actual mode/tools/errors in every report.
7. Download evidence before closing the session.
8. To recover from model failure, run a complete deterministic audit.

Handover acceptance: validate CSV/XLSX, demonstrate invalid-upload feedback, reconcile financial totals,
execute each tool, run a complete audit, test the optional model locally, inspect exports and trace,
and record the tested machine/model version. No model training or scheduled retraining is involved.

## Deployment later

The full audit application is local. A static companion report viewer is prepared for manual GitHub Pages hosting. Before public deployment add authentication/authorization, data retention policies,
secure persistent storage and access controls. Localhost Ollama means the app server’s machine, not
the visitor’s machine. Never expose an unauthenticated model endpoint or financial upload interface.
CI validates code but does not deploy or merge.

## One-command bootstrap

`start.sh` resolves the root, selects Python 3.11/3.12, creates/reuses .venv, locks setup, checks exact
distribution versions and imports, installs only when needed, preserves existing .env, generates a
missing demo, validates configuration and execs Streamlit on loopback. A failed install cannot write
a success stamp. Local model weights are managed solely by Ollama. `start.ps1` provides a Windows
equivalent but remains unverified without PowerShell on the test machine.

GitHub Pages serves only the report viewer. Its manual workflow builds a fixed fictional report; it
never publishes private uploads, serves Python or connects a public browser to a private model.

## PDF reporting extension

Report validation independently reconciles tool results, source references, financial series and
policy citations before passing an immutable Pydantic report to ReportLab. Matplotlib Agg provides
headless charts. Financial input remains CSV/XLSX; policy PDFs are separate versioned sources. No
transaction-to-PDF intermediate analysis is used. Source bytes/chunks stay in session memory.

The report panel retains PDF bytes with an input/options fingerprint. Narrow-period reaudits preserve
original row IDs and show their findings separately from the full-upload overview. The agent can
request the same deterministic service after all four checks; no arbitrary rendering code is exposed.
See [PDF reporting](pdf-reports.md) for the full schema, validation and policy grammar.


## Integrated policy intelligence and evaluation

`app/rag/index.py` extracts numbered sections with page provenance, parent/child context, applicability
and document hashes. A persistent DuckDB metadata store accompanies the FAISS index; loading checks
hashes, dimensions and row counts. Atomic replacement protects known index directories. Duplicate PDFs
are detected by bytes hash. Unknown effective dates/scope are excluded from authoritative retrieval.

Eligibility (incurred date, department and country) precedes ranking. BM25 and normalized FAISS results
can be combined using RRF, followed by optional lexical title-overlap reranking. The no-download default
is explicitly nonsemantic hashing; optional MiniLM provides semantic embeddings. Uploaded documents
require declared metadata; general table/semantic metadata extraction remains partial.

`app/rag/compliance.py` uses extracted, supported financial rules and deterministic employee/day amounts,
receipts, approvals and exceptions. Financial compliance uses all eligible supported rules rather than
assuming a top-k similarity result is authoritative. Conflicting limits require human review. Arbitrary
policy language is not converted into executable rules. `verify_index_citations` checks actual source
PDF bytes, sections and pages before PDF reporting. The older in-memory policy attachment adapter remains
supported for its narrower per-transaction rules.

`app/agents/request.py` conservatively extracts supported month/year, department and country scope.
LangGraph keeps explicit state, calls registered tools, checks structured outputs and optionally runs
policy retrieval. `app/agents/context.py` assembles SQL facts and bounded verified policy excerpts for
ChatOllama. Eight versioned prompts separate instructions from untrusted evidence. Execution details
are tool/status traces, not private chain-of-thought. Scoped results supply both dashboard and PDF.

Financial data and policy sources are runtime inputs. Generator specifications, planted labels and
questions live separately under `data/synthetic/ground_truth` and are not indexed or sent to normal
agent prompts. `app/evaluation/benchmark.py` reads labels only after retrieval and prediction, computes
metrics and writes ignored local results. Compact measured release artifacts are available to the
Evaluation Lab when local results are absent. Evaluation never modifies financial records.

See [RAG methodology](RAG_EVALUATION.md), [competency evidence](JOB_RELEVANCE_MAPPING.md) and
[the engineering report](release/ENGINEERING_REPORT.md) for actual validation and limitations.
