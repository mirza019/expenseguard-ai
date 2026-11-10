"""Transparent retrieval/grounding scoring; labels are loaded only by evaluation code."""

import hashlib
import json
import math
import time
from dataclasses import asdict

from app.rag.index import PolicyIndex, applicable

METHODS = ["bm25", "faiss", "hybrid", "reranked_hybrid"]


def retrieval_metrics(retrieved: list[str], relevant: list[str], k=5) -> dict:
    target = set(relevant)
    if not target:
        return {
            name: None
            for name in ["recall@1", "recall@3", "recall@5", "precision@5", "mrr", "ndcg@5"]
        }
    output = {
        f"recall@{cut}": len(set(retrieved[:cut]) & target) / len(target) for cut in [1, 3, 5]
    }
    output["precision@5"] = len(set(retrieved[:k]) & target) / k
    output["mrr"] = next((1 / (i + 1) for i, key in enumerate(retrieved) if key in target), 0.0)
    dcg = sum((1 / math.log2(i + 2)) for i, key in enumerate(retrieved[:k]) if key in target)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(target))))
    output["ndcg@5"] = dcg / ideal if ideal else 0.0
    return output


def mean_metrics(rows: list[dict]) -> dict:
    names = [
        "recall@1",
        "recall@3",
        "recall@5",
        "precision@5",
        "mrr",
        "ndcg@5",
        "metadata_accuracy",
        "historical_accuracy",
        "latency_ms",
    ]
    return {
        name: sum(values) / len(values) if values else None
        for name in names
        for values in [[r["metrics"][name] for r in rows if r["metrics"].get(name) is not None]]
    }


def evaluate(index: PolicyIndex, questions: list[dict], split="test", live=False) -> dict:
    records = []
    started = time.perf_counter()
    for question in questions:
        if question["split"] != split:
            continue
        for method in METHODS:
            begin = time.perf_counter()
            # Predictions see question/context only. Expected answers enter scoring below.
            hits = index.search(
                question["question"],
                question["transaction_date"],
                question["country"],
                question["department"],
                method=method,
                k=5,
            )
            refs = [h.chunk.reference for h in hits]
            expected = [
                r["document_id"] + ":" + r["section_id"] for r in question["expected_references"]
            ]
            metric = retrieval_metrics(refs, expected)
            metric["latency_ms"] = (time.perf_counter() - begin) * 1000
            metric["metadata_accuracy"] = (
                sum(
                    applicable(
                        h.chunk,
                        question["transaction_date"],
                        question["country"],
                        question["department"],
                    )
                    for h in hits
                )
                / len(hits)
                if hits
                else None
            )
            families = {
                r["document_id"].split("-policy-")[0]: r["document_id"]
                for r in question["expected_references"]
                if "-policy-v" in r["document_id"]
            }
            selected = [
                h.chunk for h in hits if h.chunk.document_id.split("-policy-")[0] in families
            ]
            metric["historical_accuracy"] = (
                sum(c.document_id == families[c.document_id.split("-policy-")[0]] for c in selected)
                / len(selected)
                if selected
                else 0
                if families
                else None
            )
            from app.rag.answers import grounded_answer, score_answer

            prediction = grounded_answer(
                index,
                question["question"],
                question["transaction_date"],
                question["country"],
                question["department"],
                hits=hits,
                transaction_context=question.get("transaction_context"),
            )
            answer_metrics = score_answer(prediction, question)
            records.append(
                {
                    "question_id": question["question_id"],
                    "question": question["question"],
                    "question_type": question["question_type"],
                    "difficulty": question["difficulty"],
                    "method": method,
                    "expected_behavior": question["expected_behavior"],
                    "expected_answer": question["expected_answer"],
                    "expected_references": expected,
                    "retrieved": [
                        {
                            "reference": h.chunk.reference,
                            "score": h.score,
                            "metadata": asdict(h.chunk),
                        }
                        for h in hits
                    ],
                    "metrics": metric,
                    "prediction": prediction,
                    "answer_metrics": answer_metrics,
                    "failed": metric.get("recall@5") is not None
                    and metric["recall@5"] < 1
                    or answer_metrics["behavior_correct"] == 0
                    or answer_metrics["answer_correct"] == 0
                    or answer_metrics.get("classification_correct") == 0,
                }
            )
    summaries = {
        method: mean_metrics([r for r in records if r["method"] == method]) for method in METHODS
    }
    by_difficulty = {
        f"{method}/{level}": mean_metrics(
            [r for r in records if r["method"] == method and r["difficulty"] == level]
        )
        for method in METHODS
        for level in ["easy", "medium", "hard"]
    }
    answer_summary = {
        method: {
            key: sum(r["answer_metrics"][key] for r in records if r["method"] == method)
            / max(1, len([r for r in records if r["method"] == method]))
            for key in [
                "behavior_correct",
                "answer_correct",
                "citation_precision",
                "citation_coverage",
                "unsupported_claim_rate",
            ]
        }
        for method in METHODS
    }
    for method in METHODS:
        classified = [
            r["answer_metrics"]["classification_correct"]
            for r in records
            if r["method"] == method
            and r["answer_metrics"].get("classification_correct") is not None
        ]
        answer_summary[method]["transaction_classification_accuracy"] = (
            sum(classified) / len(classified) if classified else None
        )
        answer_summary[method]["transaction_classification_n"] = len(classified)
    live_result = {
        "status": "not_run",
        "reason": "No explicit live-generation request; no Ollama needed.",
    }
    if live:
        from app.rag.answers import evaluate_live

        live_result = evaluate_live(index, [q for q in questions if q["split"] == split])
    return {
        "question_set_sha256": hashlib.sha256(
            json.dumps(questions, sort_keys=True).encode()
        ).hexdigest(),
        "split": split,
        "questions": len({r["question_id"] for r in records}),
        "embedding": index.embedder.name,
        "configuration": {
            "rrf_k": 60,
            "top_k": 5,
            "reranker": "local lexical section-title overlap; not neural",
            "chunk_tokens": 220,
            "overlap": 35,
        },
        "runtime_seconds": time.perf_counter() - started,
        "retrieval": summaries,
        "by_difficulty": by_difficulty,
        "answers": answer_summary,
        "live_generation": live_result,
        "records": records,
    }
