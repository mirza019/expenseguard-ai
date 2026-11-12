# Capability evidence and limitations

This document maps product claims to implementation, verification, and limitations.

| Capability | Implementation evidence | Verification | Limitation |
|---|---|---|---|
| Immutable source plus normalized analytics | `app/services/ingestion.py`, `validation.py` | ingestion, validation, edge-case tests | Arbitrary workbook layouts are not fully inferred |
| Exact financial arithmetic | `app/tools/budget.py`, `app/services/analytics.py` | budget and reconciliation tests | Current demo model is expense-centric |
| Monthly variance investigation | `app/workflows/monthly_close.py` | monthly-close tests | Observed contributors are not causal explanations |
| Governed context versions | `app/services/context_registry.py` | approval and conflict tests | Local file persistence, no authenticated RBAC |
| PDF policy intelligence | `app/rag/`, `app/services/policy_rag.py` | retrieval and policy integration tests | OCR is not bundled |
| Hybrid retrieval and citations | `app/rag/index.py`, `answers.py` | benchmark and citation tests | Neural models are optional local dependencies |
| Bounded agent orchestration | `app/agents/graph.py` | agent and model UI tests | Local 4B models can still require deterministic fallback |
| Management reporting | `app/reports/`, `app/services/reporting.py` | PDF and report-validation tests | Reports require human review |
| Local model management | `app/services/model_manager.py` | model-manager and Ollama tests | No model is silently downloaded |
| Reproducible demonstration | `scripts/generate_*`, `data/synthetic/` | manifests and deterministic tests | Synthetic results are not real-company performance claims |

Implemented, experimental, and planned features are distinguished in the README and focused design
documents. Architecture placeholders are not presented as working enterprise integrations.
