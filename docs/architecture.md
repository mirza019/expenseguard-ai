# Architecture

FinContext AI separates deterministic financial computation from probabilistic retrieval and
explanation. Financial totals never depend on an LLM response.

```text
CSV / XLSX / text PDF
        |
        v
Ingestion, profiling, immutable source copy
        |                         |
        v                         v
Validated financial model    Structured policy chunks
        |                         |
        v                         v
DuckDB / Python tools        BM25 + dense + metadata filters
        |                         |
        +-----------+-------------+
                    v
        Governed financial context registry
                    v
       Bounded workflows / LangGraph audit
                    v
     Reconciled findings and cited evidence
                    v
 Dashboard / reports / human review
```

## Design decisions

- Original data and normalized data are separate objects.
- Money is converted to integer cents; unsupported currencies are excluded explicitly.
- Budget allocation grain is month, department, and cost center. Repeated allocations are not
  summed as though they were line-item budgets.
- SQL and registered Python tools answer numerical questions. Embeddings discover knowledge, not
  transaction totals.
- Context extraction creates drafts. Only approved versions are eligible for authoritative use.
- Agent execution is allowlisted, bounded, validated, and recoverable through deterministic fallback.
- Reports consume validated result objects rather than asking a model to recalculate figures.

## Runtime boundaries

The local demo uses Streamlit session state and local files. It is not a multiuser service. A
production deployment would move datasets, context versions, run history, permissions, and schedules
to authenticated services and a background worker.
