# Synthetic policy RAG: reproducibility and evaluation

## Data boundaries

`app/rag/specification.py` is generator-only source of truth. Fifteen ReportLab PDFs cover twelve
policy families, with historical travel/meal versions and an explicitly unknown-metadata guidance
file. Each PDF has three pages: scope/controls, numerical rules/tables, exceptions/examples. Every
page/corpus is fictional. Policies use EUR, DE/FR scope and ALL/Engineering exceptions. Procurement
and delegation deliberately conflict. These are controlled templates, not a representative sample
of real corporate policy language.

`data/synthetic/expenses/` contains 2,400 fixed-seed transactions in CSV/XLSX, compatible with the
financial schema and extended with employee, country, approval, receipt and emergency evidence.
`ground_truth/` separately stores expected issues, question records and generator specification.
The normal agent never reads these labels. Financial facts come from uploaded records; policy facts
come from extracted PDFs. The index builder accepts only PDF paths in the policy catalog and refuses
the ground-truth directory. It does not index questions, labels, expected answers, specs or benchmarks.

## Rebuild commands

```bash
python scripts/generate_synthetic_policies.py
python scripts/generate_synthetic_expenses.py
python scripts/generate_rag_ground_truth.py
python scripts/build_rag_index.py
python scripts/evaluate_rag.py --split development --output data/evaluation/results/development-hash.json
python scripts/evaluate_rag.py --split test --live --output data/evaluation/results/heldout-hash.json
python scripts/generate_october_demo.py
```

Default FAISS uses a deterministic 512-dimensional normalized word/character hash-vector baseline.
It is **not semantic neural retrieval**, despite using the real FAISS library. This profile provides
fast offline regression tests and requires no downloaded model. BM25 is the rank-bm25 implementation.

### Optional neural profile (explicit setup)

For Linux CPU, install CPU Torch first to avoid unnecessary CUDA packages:

```bash
python -m pip install torch==2.9.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-embeddings.txt
python scripts/build_rag_index.py --embedding sentence-transformers/all-MiniLM-L6-v2 \
  --allow-download --output .local/rag-neural
python scripts/evaluate_rag.py --split development --index .local/rag-neural \
  --embedding sentence-transformers/all-MiniLM-L6-v2 \
  --output data/evaluation/results/development-neural.json
python scripts/evaluate_rag.py --split test --live --index .local/rag-neural \
  --embedding sentence-transformers/all-MiniLM-L6-v2 \
  --output data/evaluation/results/heldout-neural.json
```

On Apple Silicon use its compatible Torch wheel via normal pip, then the optional requirements.
The small English MiniLM encoder has 384 output dimensions and a 256-wordpiece limit. It was actually
run on CPU in this environment. Corpus inputs were checked: maximum encoded input length was 124
wordpieces, so these fixtures do not truncate. The chunk limit uses approximate whitespace tokens,
not an arbitrary model's tokenizer; new long documents require validation/reconfiguration. This is a
known limitation, not a claim of universal semantic chunking.

No embedding download happens on normal imports, startup or CI. `--allow-download` is explicit;
subsequent loads use local files only. The UI offers a cached-model profile and reports unavailable
optional models instead of silently downloading. The default corpus UI uses the offline baseline.
Model weights and local indexes are ignored by Git.

## Hierarchy, metadata and provenance

PyMuPDF extracts pages and numbered sections. Logical parent sections are retained whole; children
use configurable 220-word windows with 35-word overlap for long sections. Short rules/tables stay
intact. Retrieval expands financial-rule hits with their real exception section on a different page,
without pretending it is the same citation. Parent IDs, child/content/document hashes, section/title,
page range, version, effective period, country, department, category, approval and status are stored.
Source versions and chunks are persisted in DuckDB; vectors in FAISS. Checksums, dimensions and chunk
counts are checked at load. Rebuilds use a temporary directory and rollback-capable replacement.

Corpus applicability is supplied by its controlled specification and explicit section structure;
uploaded-policy scope is uploader-declared. Unknown dates/versions/scopes are preserved and excluded
from authoritative retrieval. This does not claim general-purpose automatic metadata extraction or
arbitrary PDF table reconstruction. Duplicate byte-identical documents are deduplicated; replacing
catalog records and rebuilding removes stale entries while explicitly retained versions remain.

## Retrieval and numerical controls

Eligibility is applied before ranking: incurred date, effective period, country, department, then
latest eligible version per title. Superseded 2025 policies remain applicable to 2025 expenses.
BM25, FAISS and reciprocal-rank fusion (`k=60`) are compared at top 5, with section deduplication.
The optional reranker adds transparent section-title keyword overlap; it is **not a neural cross-encoder**.
No ranking parameters are tuned on reported held-out scores. Final settings are recorded with results.

Numerical compliance is deterministic: recognized PDF-derived ceilings, units, receipts, approval
roles and documented Engineering emergency exceptions. Daily limits aggregate by employee/date/category.
Unknown employees, countries or control evidence abstain; incompatible applicable ceilings escalate.
Unrecognized policy grammar is not silently treated as compliant. Arbitrary real-policy interpretation
still needs human validation. Invoice date defines financial periods; an explicit transaction date,
when supplied, determines policy applicability. Invalid incurred dates do not authorize a policy verdict.

## Ground truth, split and scoring

196 questions cover fourteen categories, including paraphrases, cross-document/section cases,
versions, country/department tables, exceptions, transaction controls, unanswerable prompts, conflicts
and injection attempts. Expected facts come from the structured generator, never from model output.
Development has 110 questions; held-out has 86. Rule families are grouped where practical; exact
question overlap across the splits is tested. Conflict/unanswerable scenarios have distinct dated
contexts across splits. Templates/boilerplate still overlap: this is not a blind independent natural-
language benchmark, and integration runs accessed the held-out set. No production generalization
claim is justified. Final retrieval settings remained fixed rather than optimized to those scores.

Relevant items are unique document/section pairs. Recall@1/3/5 measures recovered relevant pairs;
Precision@5 divides relevant retrieved pairs by five; MRR uses the first relevant rank; nDCG@5 uses
binary relevance. Unanswerable questions have no relevance denominator and are excluded from retrieval
averages, but are scored for abstention. Results include difficulty breakdowns and question-level
failures. Metadata accuracy validates emitted-hit eligibility, not metadata-extraction accuracy;
historical accuracy examines retrieved members of expected policy families. Independent regression
cases verify known date/country/department outcomes.

Deterministic answer checks are deliberately transparent proxies: expected numeric-token inclusion
plus behavior, expected-reference precision/coverage, and strict source-supported extractive claims.
They are **not human semantic answer accuracy**. Extra irrelevant citations lower precision even when
numbers are present; high Recall/MRR must not hide that weakness. Transaction classifications have a
separate accuracy and denominator. These controls are deterministic evaluations, not Qwen inference.

`--live` checks Ollama readiness. If absent it records **skipped**, continues retrieval, and downloads
nothing. If ready, ChatOllama generates structured answers from retrieved text only. Fabricated
citations fail validation; exact source-overlap scoring is conservative and can penalize legitimate
paraphrases. Human review is still required for semantic correctness and causal interpretations.

## Inspect and reproduce results

Open **RAG Evaluation Lab**. Compare methods, filter difficulty/type, inspect expected versus retrieved
references, scores, metadata and failed questions, and download results. Full runtime results are
ignored under `data/evaluation/results`; compact measured release artifacts are tracked under
`docs/release/benchmarks` and used as a read-only UI fallback when no local benchmark exists.

Ordinary CI runs small deterministic fixtures and mocked model tests. The optional manual benchmark
workflow runs the complete offline corpus. Neither downloads Qwen or embedding weights. See the
release engineering report for measured scores, provenance, runtime and limitations.
