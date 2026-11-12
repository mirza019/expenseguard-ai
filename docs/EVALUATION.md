# Evaluation

The repository contains reproducible policy documents, ground-truth questions, transaction labels,
and benchmark scripts. Ground truth is stored separately from indexed evidence.

Retrieval evaluation reports Recall@1/3/5, Precision@5, MRR, nDCG@5, citation behavior,
applicability, answer behavior, and latency where supported by the current benchmark. Deterministic
hash retrieval and optional local neural retrieval can be compared without inventing results.

Agent tests cover tool choice, invalid decisions, bounded retries, deterministic fallback, financial
reconciliation, evidence references, PDF validation, and missing Ollama behavior.

Run:

```bash
python scripts/evaluate_rag.py
pytest -q
```

Committed benchmark summaries identify their profile and fixtures. They are not universal product
accuracy claims. The requested 150-question, multilingual, reranker comparison is a future benchmark
expansion; current documentation must report the actual fixture count.
