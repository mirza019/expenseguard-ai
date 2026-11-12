# Retrieval engine

FinContext AI routes questions according to evidence type.

## Structured financial retrieval

Transactions, budgets, filters, groupings, reconciliation, duplicates, and trends use DuckDB or
registered deterministic Python tools. The system does not embed every transaction row and does not
use an LLM to calculate totals.

## PDF knowledge retrieval

PyMuPDF extraction preserves document, section, page, version, effective date, geography, department,
and source references. Hierarchical chunks retain parent context. Retrieval supports BM25, a local
dense profile, reciprocal-rank fusion, metadata filtering, and citation verification.

Textless/scanned PDFs are reported as requiring OCR. The application never pretends extraction
succeeded.

## Spreadsheet knowledge

The current product reliably ingests transaction-style sheets. Extraction of arbitrary glossary,
notes, formulas, hidden layout, and multi-table worksheets remains experimental and must not be
confused with the implemented transaction pipeline.

## Evaluation

Ground truth remains separate from the index. Evaluation covers retrieval rank, citation references,
applicability, answer behavior, and latency. See [EVALUATION.md](EVALUATION.md).
