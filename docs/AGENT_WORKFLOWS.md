# Agent workflows

## Monthly Financial Review & Variance Investigation

The primary workflow selects a reporting period, validates eligible rows, reconciles represented
budgets, ranks material department variances, identifies arithmetic category contributors, checks
unusual expenses, and produces a draft awaiting human review.

It explicitly distinguishes observed contributors from confirmed causes. For example, a category may
compose most of a variance while the operational reason remains unknown.

## Expense compliance audit

The reusable secondary workflow runs four verified tools: duplicates, budget, anomalies, and missing
data. Optional policy evaluation adds historically applicable citations.

## Agent boundaries

- LangGraph state and Pydantic decisions.
- Registered, read-only tools only.
- Maximum calls and retries.
- No repeated unavailable tool calls.
- Independent result validation and reconciliation.
- Explicit deterministic fallback when Ollama is missing or invalid.
- Human review before reports become final.

Manual execution is implemented. Durable scheduled and event-driven execution requires a background
worker and is planned rather than simulated inside Streamlit.
