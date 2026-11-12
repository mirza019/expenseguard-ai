# FinContext AI — engineering verification report

Verified locally on Linux/Python 3.12, 10 November 2026. This extends the existing implementation;
it does not replace it. Stable `main` remains the original scaffold pending review. All implementation
work is preserved on `docs/project-documentation` for PR #1. No automatic merge or deployment occurs.

## A. Feature completion matrix

| Feature | Status | Actual source | Test / verification evidence and gap |
|---|---|---|---|
| CSV/XLSX bounded ingestion | Implemented and tested | services/ingestion.py, validation.py | ingestion/validation tests; original retained, malformed/unsupported records reported |
| Column normalization and policy dates | Implemented and tested | services/validation.py | RAG/integration tests; alias collision rejected, incurred vs invoice dates distinct |
| Four deterministic audit tools | Implemented and tested | app/tools/ | duplicates, budget, anomalies, missing-data tests and full workflow |
| SQL summaries / reconciliation | Implemented and tested | database/duckdb_service.py, services/analytics.py | fixed SQL queries; exact-cents reconciliation tests |
| Planning / variance contribution | Implemented and tested | services/planning.py | test_planning.py; scenario and conditional run-rate; not trained forecasting |
| LangGraph orchestration / scoped state | Implemented and tested | agents/graph.py, state.py, request.py | agent tests and test_policy_intelligence.py; bounded financial/policy actions |
| ChatOllama / Qwen / setup | Implemented and tested with mocks; live blocked | agents/finance_agent.py, services/model_manager.py | mocked download/inference/error/retry tests; Ollama unavailable locally |
| Modular context / prompts | Implemented and tested | agents/context.py, app/prompts/ | assembled verified SQL/policy context and mocked integration; no live linguistic quality claim |
| PDF extraction and numbered sections | Implemented and tested | rag/index.py | generated PDF page/section tests; scanned PDFs rejected |
| Parent-child context / exceptions | Implemented and tested for fixture; generality partial | rag/index.py | separate-page exception regression; approximate word limits, no universal table parser |
| Metadata / version storage | Implemented and tested | rag/index.py | DuckDB metadata, checksums, unknown applicability, duplicate/replacement/corruption tests; metadata must be declared for uploads |
| FAISS / BM25 / RRF | Implemented and tested | rag/index.py | actual persisted index; retrieval regression and full measured benchmark |
| Semantic SentenceTransformers | Implemented and locally evaluated | rag/index.py, requirements-embeddings.txt | real MiniLM CPU inference, 384 dimensions; optional installation, no CI download |
| Reranking | Implemented and tested, limited | rag/index.py | lexical title overlap; neural cross-encoder not implemented |
| Historical / country / department eligibility | Implemented and tested | rag/index.py, compliance.py | date-before-ranking and October 2025 historical-limit tests |
| Policy compliance | Implemented and tested for supported rules | rag/compliance.py | thresholds, per-day aggregation, receipts, authority, exceptions, conflicts; arbitrary legal/business prose requires human review |
| Source-verified citations | Implemented and tested | rag/compliance.py, services/report_validation.py | real bytes hash/section/page validation, fabricated/stale source rejection |
| Synthetic corpus and labels | Implemented and tested | rag/specification.py, datasets.py, scripts/generate_* | 15 PDFs, 45 pages, 2,400 CSV/XLSX rows; fixed-seed byte reproducibility and separate labels |
| Ground truth and benchmark | Implemented and tested | evaluation/benchmark.py, rag/answers.py | 196 questions, 110 development / 86 held-out; actual metrics and failure records |
| Grounded live Qwen evaluation | Implemented, live execution blocked | rag/answers.py | structured mocked inference succeeds; real evaluation explicitly skipped |
| Green workflow dashboard | Implemented and browser inspected | app/main.py, app/ui/* | eight tabs, actual desktop/mobile captures, no JS page errors or horizontal overflow |
| Filterable findings / raw-row export | Implemented and tested | ui/findings.py | integrated AppTest; distinct policy/evidence statuses, spreadsheet-safe CSV |
| PDF audit reports | Implemented and tested | app/reports/*, services/report_validation.py | rendered A4, long tables, Unicode, reconciliation, indexed policy integration; no LLM needed |
| Startup / configuration / CI | Implemented and locally tested | start.sh, scripts/check_environment.py, workflows/ | actual launcher reused dependencies and served Streamlit; shell/pytest checks |
| Windows and target Mac runtime | Implemented but not fully validated | start.ps1, start.sh | Linux verified; PowerShell and Mac M3 performance not executed |
| Authenticated multiuser/ERP/SSO | Missing, outside local reference scope | — | no claim of production finance-system integration |
| Optional evaluation PDF | Not implemented (optional) | — | measured JSON downloads and Evaluation Lab available |

Paths abbreviated above are under `app/` unless otherwise stated. Initial gaps are preserved in
[INITIAL_FEATURE_AUDIT.md](INITIAL_FEATURE_AUDIT.md). Tests prove exercised behavior, not merely file existence.

## B. UI/UX review

The existing application now uses warm white/pale sage, emerald accents, readable financial tables,
semantic warning/error states and restrained KPI cards. Navigation follows Overview → Data Workspace
→ Policy Knowledge Base → AI Audit Assistant → Audit Findings → Reports → RAG Evaluation Lab → System
Status. Charts use consistent EUR units, sorted categories and chronological dates. Period/source changes
invalidate audit/PDF caches. A scoped agent audit supplies the dashboard and PDF from the same frame.

Actual Chromium/Playwright inspection loaded 2,400 records, rebuilt policies, ran a complete audit and
captured every section at 1440×1000 plus Overview at 390×844. Browser page errors: **0**. Horizontal
mobile document overflow: **false**. Screenshots in `docs/screenshots` are actual application captures.
Overview typography, card alignment and source/AI status were visually inspected. The actual browser also selected October 2025, ran the indexed-policy audit, generated and downloaded
a readable **14-page PDF (152,940 bytes)**, and verified its EUR 6,220.13 total. Browser screenshots do
not prove accessibility certification or Mac/Safari behavior. Long tables retain native scrolling.

## C. RAG evaluation

Corpus: **15 synthetic PDFs, 3 pages each; 150 indexed chunks; 2,400 transactions; 196 questions**.
The twelve required policy topics include historical travel/meal versions and unknown-metadata guidance.
Development: 110 questions. Held-out regression split: 86 questions; 79 have retrieval references.
Split SHA256: `41e36d560ebeaa613246d19adfe025d131ed1cafec7cc251f2ec87c69d185ee9`.

Real CPU `sentence-transformers/all-MiniLM-L6-v2` evaluation:

| Method | R@1 | R@3 | R@5 | P@5 | MRR | nDCG@5 | Mean query ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 | .1646 | .9135 | .9135 | .2354 | .5949 | .6641 | 1.49 |
| FAISS | .7996 | .9177 | .9262 | .2430 | .9873 | .9311 | 19.04 |
| Hybrid | .6076 | .9135 | .9135 | .2354 | .8797 | .8491 | 20.20 |
| Lexically reranked hybrid | .8249 | .9135 | .9135 | .2354 | 1.0000 | .9311 | 18.96 |

Full held-out neural evaluation: **7.18 seconds**. Hashing baseline: **2.02 seconds**; its FAISS R@5
was .9072 and MRR .7603. Metadata output eligibility and historical selection scores were 1.0 where
defined. Eligibility shares the implementation predicate and is not an independent metadata-extraction
accuracy assessment. Difficulty-specific scores and every prediction are in measured release JSON.

FAISS deterministic answer proxy: behavior/numeric-token score 1.0, citation precision **.525**, citation
coverage **.9671**. Six held-out transaction classifications passed. Source-extractive unsupported-claim
rate was zero by construction, not proof of semantic truth. Failures across 344 method/question rows:
**62 neural / 77 hashing** under recall, behavior, numeric and classification checks. Broad context
retrieval introduces irrelevant citations; this remains a documented quality limitation.

**Live Qwen generation: skipped, Ollama unavailable.** No invented generation metrics. Parameters were
fixed across development/test runs. Held-out cases were inspected during integration; repeated template
language remains. This is an inspectable regression benchmark, not a pristine blind generalization study.
See [methodology](../RAG_EVALUATION.md) and [measured artifacts](benchmarks/).

## D. Financial accuracy

Full deterministic tests independently check budget grain, repeated allocations, invalid data exclusion,
exact cents, chart/SQL totals, duplicate references and report reconciliation. The October 2025 demo
contains **101 records**, **EUR 6,220.13 actual**, **EUR 9,000 represented budget** and **−EUR 2,779.87
variance**. Finance exceeds its represented budget by **EUR 191.86** despite overall underspend.
Seventeen potential policy violations and one financial finding yield **EUR 4,727.21** unique recorded
expense requiring review, not loss. The historical EUR 50 meal is compared to the 2025 EUR 40 limit.

Scenario tests independently verify 10% of EUR 600 = EUR 60 and conditional annualization of three
complete months to EUR 2,400. Real scenario outputs disclose recorded-category and completeness
assumptions. Monthly category contributions describe arithmetic changes; causal explanations require
additional evidence. No untrained forecast is presented as predictive model accuracy.

## E. Agent reliability

Actual graph tests cover structured registered tool execution, validation, inspection, bounds, retries,
invalid references, unavailable LLM, source failure and deterministic fallback. The October graph trace
executes duplicates, budget, anomalies, missing data and applicable policy evidence. SQL/numerical facts
come from Python/DuckDB; model actions cannot execute unrestricted code or alter records/payments.
Unknown approval authority and unsupported emergency claims yield evidence-incomplete results.
ChatOllama behavior is tested with mocked responses; real Qwen decision quality remains unverified.

## F. Testing and CI

Executed locally:

- `python -m pytest --cov --cov-report=term-missing --cov-report=xml`: **131 passed in 134.98s**.
- Core/RAG/reporting statement coverage: **96.28%**, 1,857 statements, 69 uncovered; 80% gate passed.
- `ruff check .` and `ruff format --check .`: passed (94 Python files).
- `bash -n start.sh` and `python scripts/check_environment.py`: passed.
- `node --test tests/frontend/report.test.mjs`: **3 passed**.
- Both development and held-out benchmarks for hashing and real MiniLM: executed successfully.
- Actual `./start.sh --server.port 8507`: reused environment and launched Streamlit locally.
- Chromium screenshots and integrated demo audit: executed; rendered PDF layout also tested by pytest.

Ordinary GitHub Actions matrix targets Python 3.11/3.12 and includes Ruff, tests, imports, shell/config,
frontend checks and headless PDF regression. The optional manual benchmark workflow downloads no models.
Remote CI status is recorded in the PR; local success is not a substitute for a remote run.

## G. Demonstrated capabilities

Actual demonstrated skills: financial variance and cost-center accountability; financial data validation and
SQL reconciliation; deterministic risk screening; hierarchical context, metadata, historical retrieval
and grounded citations; bounded LangGraph tool execution; local application delivery, testing and
reporting. See [CAPABILITY_EVIDENCE.md](../CAPABILITY_EVIDENCE.md) for feature, source, test and
business-outcome examples. Capabilities not implemented in this repository are not claimed.

## H. Remaining limitations

Live Qwen inference/model download, Apple Silicon latency and Windows startup remain unverified. Corpus
is fictional, templated and English; arbitrary PDF table reconstruction/automatic metadata inference is
partial. Chunk sizes use approximate words; maximum measured synthetic MiniLM input was 124 subword
tokens, below the 256-token model limit, but arbitrary uploads need broader tokenizer-aware validation.
The reranker is lexical, answer correctness a transparent proxy and six classification examples too few
for general accuracy claims. Policy controls support a defined grammar, not arbitrary legal language.
Only EUR nonnegative expenses are supported. Budgets reflect represented groups only. Forecasting is
conditional run-rate, not trained ML. No case persistence, ERP, SSO or production access controls exist.
No deployment or main merge was performed.

## I. Release recommendation

**Ready with documented limitations.** Deterministic auditing, supported policy intelligence, PDF export,
measured retrieval, startup and the rendered interface have concrete passing evidence. Present using
the reproducible October walkthrough and explicitly disclose local-model and general-document limitations.
Do not present this reference release as a certified audit, an independently validated compliance engine
or a production financial system.
