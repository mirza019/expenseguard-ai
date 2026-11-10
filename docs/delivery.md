# Delivery and review map

## Review entry point

Complete integration PR: https://github.com/mirza019/expenseguard-ai/pull/1

Main is unchanged. Do not independently merge the overlapping milestone drafts below; their
cumulative changes and later fixes are all represented in the integration PR.

| Branch | Draft PR | Milestone commit |
|---|---|---|
| feature/csv-upload | #2 | ec13906 |
| feature/expense-validation | #3 | 5869e07 |
| feature/duplicate-detector | #4 | 8f4f4d6 |
| feature/budget-checker | #5 | d380e2f |
| feature/anomaly-detector | #6 | 75258f9 |
| feature/ai-agent | #7 | 45d2dd6 |
| feature/report-dashboard | #8 | d61bb03 |
| feature/ci-tests | #9 | 03ddbc6, 6da1157 |
| docs/project-documentation | #1 | ef94f57 plus final verification fixes |

Historical branches contain intermediate code; only the integration head is the final tested product.
Older CI failures on intermediate snapshots are not the current integration result.

## Final structure

```text
app/
  main.py, config.py, agent.py
  agents/finance_agent.py, graph.py, state.py
  tools/duplicates.py, budget.py, anomalies.py, missing_data.py
  services/ingestion.py, validation.py, analytics.py, reporting.py
  database/duckdb_service.py
  ui/upload.py, dashboard.py, agent_panel.py
tests/unit/ and tests/integration/
data/synthetic_expenses.csv and synthetic_expenses.manifest.json
scripts/generate_data.py
docs/architecture.md, agent-workflow.md, testing.md, delivery.md
.github/workflows/ci.yml and pull_request_template.md
.streamlit/config.toml
.env.example, .gitignore, requirements.txt, pyproject.toml, Makefile, README.md, LICENSE
```

All packages include initialization modules. The legacy three-row sample remains for provenance.

## Demonstration

1. Start Streamlit and load the fictional sample.
2. Show original versus normalized data and excluded rows.
3. Inspect department spend and budget comparisons.
4. Run individual duplicate and budget checks and inspect source references.
5. Run the complete deterministic audit and download JSON evidence.
6. With local Ollama running, submit a focused goal and inspect tool selection/trace.
7. Without Ollama, demonstrate the labeled fallback rather than claim an AI response.

## Verification boundary

111 tests passed with 97.72% core/reporting statement coverage; three frontend tests passed on Linux/Python 3.12.14; lint/formatting passed.
Streamlit AppTest completed sample loading and the full audit. A real Streamlit server was started
and its local /_stcore/health endpoint returned `ok`. No production deployment or merge was performed.
Live Qwen inference, a real model download, Mac hardware performance, Windows PowerShell execution and a real browser screenshot remain unverified.

## Follow-up: one-command setup and local AI management

Main was reinspected and still contains only the scaffold. Active PR #1 preserves the complete
unmerged prerequisite work. Consequently the follow-up stays on docs/project-documentation; the
older feature/ai-agent is not reset, rebased or overwritten, and no conflicting branch is created
from incomplete main. This implements the user's active-task-branch exception. Main is unchanged.

New components: start.sh, optional start.ps1, scripts/check_environment.py, the SDK model manager,
startup AI sidebar, LangChain ChatOllama inference, registered StructuredTools, static GitHub Pages
report viewer, and manual-only Pages workflow. No automatic model download, merge or deployment.

After review, enable Pages → GitHub Actions and manually dispatch the companion workflow. The
static viewer does not replace the local Python/Ollama audit application.

## PDF report extension

The current branch remains the safe integration branch because main still contains only the scaffold.
The PDF feature adds validated Pydantic report data, deterministic reconciliation, ReportLab A4 layout,
Matplotlib Agg charts, page-aware PyMuPDF policy retrieval/citation checks, period-specific audits,
Streamlit preview/download/cache controls and an optional LangGraph generation action.

The repository previously had no policy retrieval implementation; the new in-memory adapter is
explicitly lexical and supports narrow category-limit rules. It does not claim full semantic policy
understanding or exhaustive compliance. Other retrieved passages remain guidance.

Example: docs/examples/ExpenseGuard_Synthetic_Audit_Report.pdf (11 pages, about 175 KB), with a
fictional policy PDF and a reproducible generation script. No confidential data is committed.
