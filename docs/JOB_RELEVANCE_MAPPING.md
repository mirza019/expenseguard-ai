# Feature-to-competency mapping

This project is an independent synthetic-data portfolio, not a Siemens Energy deployment. No exact
FP&A / AI & Context Engineer posting was supplied for this release; mapping uses the requested
competencies. An earlier conversation supplied a different Gas Services Sales Intelligence & AI
posting. This expense platform does not implement turbine pricing, CRM integration, Orion, SAP,
Snowflake, Azure or production financial systems and must not be presented as doing so.

## 1. Expense preparation and reconciliation
- Purpose/problem: make heterogeneous expense exports analyzable without hiding invalid records.
- Competency: financial data preparation, controlled normalization and reconciliation.
- Implementation: `services/ingestion.py`, `validation.py`, `database/duckdb_service.py`.
- Sources/calculation: original CSV/XLSX preserved; normalized names/aliases and exact cents; EUR only;
  invalid financial rows explicitly excluded; SQL dimensions reconcile to eligible totals.
- Evidence: ingestion/validation tests, independent monetary examples, CSV→audit→PDF integration.
- User question: “Which records prevent a reliable October expense analysis?”
- Output/decision: source-row quality issues and exclusions; request corrections before interpretation.
- Interview explanation: separate original/analytical representations and exact financial arithmetic.
- Hiring-manager demo: upload malformed data, show a source row and explain its exclusion.

## 2. Budget-versus-actual and cost-center accountability
- Problem: repeated allocations in transaction exports can inflate budget totals.
- Competency: FP&A variance analysis, cost controlling and dimensional spend accountability.
- Implementation: `tools/budget.py`, SQL summaries and dashboard.
- Calculation: actual − budget; one allocation per month/department/cost center; zero/unknown budgets
  cannot produce a valid percentage. No enterprise allocation engine is claimed.
- Evidence: independent 60+70 actual versus 100 allocation test; conflict/zero-budget tests.
- Question: “Which departments exceeded their represented allocation, and by how much?”
- Output/decision: grouped actual/budget/variance, prioritize cost-center-owner review.
- Interview: show the grain and explain why row-level repeated budgets must not be summed.
- Demo: compare a chart with its SQL/table totals and drill into affected records.

## 3. Expense trends and arithmetic drivers
- Problem: an apparent monthly increase needs an evidence-backed baseline.
- Competency: financial performance monitoring and variance interpretation.
- Implementation: `services/planning.py`, `ui/dashboard.py`.
- Calculation: adjacent-month deltas and category contributions; missing months are not zero-filled.
- Evidence: planning tests with known monthly amounts and reporting-period integration.
- Question: “Which categories account arithmetically for the latest spending change?”
- Output/decision: category movement, then investigate invoice timing, business scope and approvals.
- Interview: distinguish an arithmetic driver from a proven operational cause.
- Demo: compare two months and trace their category totals back to source rows.

## 4. Scenarios and conditional year-end run rate
- Problem: assess a discretionary reduction without pretending it is a forecast guarantee.
- Competency: financial planning assumptions and decision support.
- Implementation: `planning_insights`, dashboard scenario controls.
- Calculation: chosen reduction × recorded Travel/Meals/Hotel expense; optional YTD average ×12 only
  after explicit complete-month assumption and contiguous elapsed-month coverage.
- Evidence: 600 EUR recorded baseline produces 60 EUR savings at 10%; 3-month run-rate example test.
- Question: “What recorded financial impact would a 10% discretionary reduction imply?”
- Output/decision: labeled estimate, assumptions and scope; review feasibility with owners.
- Interview: explain why no trained forecasting accuracy or seasonality model is claimed.
- Demo: alter the slider and confirm the exact numerical response; toggle run-rate assumptions.

## 5. Duplicate and unusual-expense review
- Problem: repeated invoices and outliers warrant investigation, not automatic fraud allegations.
- Competency: financial risk screening and internal controls.
- Implementation: deterministic duplicate and category-IQR tools.
- Calculation: documented invoice/vendor/amount/date rules; Q3+1.5×IQR with minimum sample size.
- Evidence: planted exact/possible duplicates, large amounts and small-cohort regression tests.
- Question: “Which recorded expenses need further investigation?”
- Output/decision: transaction references, thresholds and supporting evidence; inspect invoices.
- Interview: explain false positives, grouping, retained duplicates and overlapping exposure.
- Demo: open a finding and its original rows. No trained fraud ML is claimed.

## 6. Policy-aware financial controls
- Problem: a newer policy may be wrong for an older transaction; approvals/exceptions matter.
- Competency: expense compliance support, evidence traceability and internal controls.
- Implementation: `rag/compliance.py`, metadata eligibility and indexed PDF citations.
- Calculation: PDF-derived limits, daily employee totals, receipt/role checks, documented exceptions;
  conflicting policies escalate, missing evidence abstains.
- Evidence: October 2025 meal amount 50 EUR compared with 40 EUR v1 rather than 60 EUR v2;
  separate invoice/incurred-date, director exception and authority tests.
- Question: “Which October expenses exceed applicable rules or lack adequate evidence?”
- Output/decision: potential exceptions versus incomplete/conflicting evidence; human review required.
- Interview: demonstrate metadata before similarity and deterministic numbers before explanations.
- Demo: open policy section/page and show the relevant approval/exception evidence.

## 7. Context engineering and hybrid retrieval
- Problem: policy context spans sections, dates, tables and contradictory sources.
- Competency: document preprocessing, provenance, metadata design, embeddings and retrieval.
- Implementation: `rag/index.py`, DuckDB metadata, FAISS, BM25, RRF, parent expansion.
- Sources: only policy PDFs/catalog metadata; no ground-truth question or label indexing.
- Evidence: reproducibility, hierarchy, table/unit, applicability, duplicate/rebuild/checksum tests;
  actual MiniLM CPU benchmark plus model-free baseline.
- Question: “What evidence and exceptions support this limit on the transaction date?”
- Output/decision: ranked, versioned references with source pages and context.
- Interview: explain encoder tradeoffs, RRF and why reranking is local lexical rather than neural.
- Demo: compare actual failed questions in the Evaluation Lab instead of hiding weaknesses.

## 8. Bounded agentic investigation
- Problem: coordinate numerical checks and evidence without trusting generated financial values.
- Competency: agent engineering, controlled tool use and context assembly.
- Implementation: LangGraph state, LangChain tools, ChatOllama, Pydantic actions, versioned prompts.
- Calculation/source: deterministic tool outputs and policy retrieval; conservative request parameters
  support month/year, named departments and DE/FR; other scope needs explicit controls.
- Evidence: tool/state/retry/fallback tests, mocked inference and October scoped-agent integration.
- Question: “Audit October 2025 expenses and identify the main review priorities.”
- Output/decision: verified findings and allowed investigation actions; no record/payment mutation.
- Interview: distinguish tested mocked inference from unavailable live Qwen evaluation.
- Demo: show concise tool activity and deterministic fallback, never raw chain-of-thought.

## 9. Reporting and auditability
- Problem: finance managers need a readable report with reconciled figures and traceable evidence.
- Competency: financial reporting and clear professional communication.
- Implementation: Pydantic report validation, ReportLab, Matplotlib Agg, Streamlit preview/download.
- Calculation: re-execute/reconcile financial results, verify indexed citations and chart/table totals.
- Evidence: actual rendered A4 pages, text bounds/overlaps, Unicode/long tables, cache/download tests.
- Question: “Can I substantiate every flagged amount and policy reference in this report?”
- Output/decision: source-linked report and flagged-row CSV; preserve findings for human review.
- Interview: show one number from CSV through SQL/tool, UI and PDF; explain no certified-audit claim.
- Demo: export the October RAG report and locate the historical case and its source.

## 10. Evaluation, delivery and reliability
- Problem: a convincing demonstration needs measured quality and reproducibility, not technology names.
- Competency: AI application delivery, QA, CI and evidence-based engineering communication.
- Implementation: generation/evaluation CLIs, split labels, regression tests, CI, startup and green UI.
- Sources/calculation: source-of-truth labels, actual rankings, explicit metric denominators and runtimes.
- Evidence: release benchmark JSON, final test/CI records, real Chromium desktop/mobile screenshots.
- Question: “Where does retrieval fail, and can another developer reproduce that failure?”
- Output/decision: failure inspection, documented limitations and prioritized improvements.
- Interview: explain low citation precision despite high recall and the limits of numeric answer proxies.
- Demo: launch with `./start.sh`, inspect a benchmark failure and show its reproduction command.

## Not claimed

Production ERP/SSO integration, full accounting close, certified audit assurance, arbitrary policy
understanding, robust general table extraction, neural reranking, a trained financial forecast,
validated real-world fraud detection, live Qwen quality or Mac performance are not demonstrated.
