# Financial analytics

## Normalized model

The implemented model includes transaction ID, invoice ID/date, vendor, department, cost center,
category, amount, currency, represented budget, description, and payment status. Source row lineage is
retained.

## Formulas

- Actual expense = sum of eligible transaction amount cents.
- Budget variance = actual expense − represented budget.
- Variance percentage = variance / budget × 100 when budget is known and nonzero.
- Positive variance means recorded expense exceeds represented budget.

Budgets are resolved at month / department / cost-center grain. A missing or conflicting allocation is
unknown, not zero. Duplicate candidates remain in actuals until a human confirms treatment.

## Reconciliation

Tool validation checks source-row references, finite numerics, group arithmetic, total actuals, and
complete-budget totals. Dashboard and PDF layers consume these same results.

Forecast ingestion, account hierarchies, and separate ERP actual/budget/forecast fact tables are
planned extensions and are not claimed as complete.
