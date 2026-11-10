# Synthetic reporting examples

- `ExpenseGuard_Synthetic_Audit_Report.pdf`: generated from the first 100 rows of the fixed-seed
  fictional expense dataset. Fixed report timestamp: 2026-11-10 UTC.
- `fictional_expense_policy.pdf`: invented demonstration policy, version 1.0, effective 2025-01-01.
  Its explicit Travel threshold supports one potential exception in this sample.

These are demonstration artifacts, not company policies or certified audit conclusions. No AI model
was used to generate financial facts. Rebuild with `python scripts/generate_sample_report.py`.
PDF internals may include runtime-generated identifiers; reproducibility concerns the source and facts.
