# Interview demonstration: Audit October 2025 expenses

This scenario uses the generated 2,400-row fictional dataset and versioned fictional policies.
Numbers below are reproducible outputs, not invented targets; the JSON artifact is authoritative.

## Prepare

```bash
./start.sh
# In another activated environment, if regenerating:
python scripts/generate_synthetic_policies.py
python scripts/generate_synthetic_expenses.py
python scripts/generate_rag_ground_truth.py
python scripts/build_rag_index.py
python scripts/generate_october_demo.py
```

1. **Data Workspace:** load the 2,400-transaction policy demo or upload its CSV/XLSX. Show preserved
   source records, EUR validation, date aliases, employee/country/approval/receipt fields.
2. **Policy Knowledge Base:** load/rebuild the corpus. Show 15 documents, v1/v2 effective dates,
   country/department metadata, parent sections, real page references and an unknown-metadata record.
3. **Scope:** set financial analysis start/end to October 2025. Alternatively, with Qwen available
   ask “Audit October 2025 expenses.” The conservative request parser applies the same scope.
4. **Run Full Audit:** execute duplicate, budget, IQR and quality checks, then policy retrieval and
   deterministic controls. Use actual tool activity, not a claim that deterministic mode is AI.
5. **Budget investigation:** the reproducible scope has 101 source rows, EUR 6,220.13 recorded expenses,
   EUR 9,000 represented budget and EUR -2,779.87 actual-minus-budget variance. This is below budget,
   not an overrun. Explain the represented allocation grain and inspect departmental differences.
6. **Policy investigation:** the scope has 17 potential exceptions and 84 within-supported-control
   outcomes. Open RAG-TX-00007: EUR 50 incurred on 2025-10-15 must use a EUR 40 v1 meal ceiling;
   the EUR 60 rule begins in 2026. Trace document version, section 2.1, page 2 and source transaction.
7. **Risk interpretation:** EUR 4,727.21 is recorded expense in the union of rows needing review in
   this scenario, not a proven loss or the sum of overlapping findings. Show the independent
   `recorded_review_exposure_cents` calculation in the JSON artifact.
8. **Planning:** use the 10% discretionary scenario. Explain its selected categories and exact
   baseline, and why a monthly single-period extract cannot establish a reliable year-end forecast.
9. **AI explanation:** if Qwen is running, show approved, evidence-linked investigation actions. If
   absent, show the deterministic summary and explicitly state that live inference was not run.
   Do not invent operational causes. Ask the owner to review receipts, approvals and exceptions.
10. **Reports:** generate the PDF from the same scoped audit, inspect historical policy evidence,
    download flagged transactions and trace the selected row back to the source PDF/CSV.
11. **RAG Evaluation Lab:** select held-out neural results, compare retrieval methods, inspect a
    failed multi-section/cross-document question and explain citation precision versus recall.

## Artifacts

- `docs/release/OCTOBER_2025_DEMO.json`: exact calculations, scope, policy counts and execution trace.
- `docs/examples/ExpenseGuard_October_2025_RAG_Audit.pdf`: actual generated report.
- `data/synthetic/ground_truth/transaction_labels.json`: generator-only planted cases; not agent input.

These facts describe this fixed-seed fixture only. Regeneration with different parameters requires
new expected results and fresh evaluation; never copy the stated amounts to another dataset.
