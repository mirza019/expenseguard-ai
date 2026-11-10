"""Evaluation-only UI: expected labels never enter normal audit prompts or indexes."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]


def evaluation_lab() -> None:
    st.subheader("RAG Evaluation Lab")
    st.caption(
        "Measured retrieval benchmarks and inspectable failures. This page alone reads evaluation labels."
    )
    files = sorted(
        (ROOT / "data/evaluation/results").glob("*.json"),
        key=lambda p: ("heldout" not in p.name, p.name),
    )
    if not files:
        files = sorted((ROOT / "docs/release/benchmarks").glob("*.json"))
    if not files:
        st.info(
            "No benchmark results yet. Generate the corpus, build an index and run scripts/evaluate_rag.py."
        )
        return
    path = st.selectbox("Benchmark result", files, format_func=lambda p: p.name)
    try:
        result = json.loads(path.read_text())
    except (ValueError, OSError):
        st.error("Cannot read benchmark result.")
        return
    st.caption(
        f"Embedding: {result['embedding']} · Split: {result['split']} · Runtime: {result['runtime_seconds']:.2f}s"
    )
    a, b, c = st.columns(3)
    a.metric("Questions", result["questions"])
    b.metric("Methods", len(result["retrieval"]))
    c.metric("Live Qwen evaluation", result["live_generation"]["status"])
    table = pd.DataFrame(result["retrieval"]).T.reset_index(names="method")
    st.dataframe(table, hide_index=True)
    st.plotly_chart(
        px.bar(
            table,
            x="method",
            y=["recall@1", "recall@3", "recall@5", "mrr"],
            barmode="group",
            title="Measured retrieval quality on the selected split",
            range_y=[0, 1],
            labels={"value": "Score (0–1)", "method": "Retrieval method"},
            color_discrete_sequence=["#105C48", "#167D61", "#82AC96", "#C2DACC"],
        ),
        width="stretch",
    )
    st.subheader("Grounded answer checks — deterministic proxy scores")
    st.caption(
        "Answer correctness is a numeric-token + behavior proxy, not a human semantic assessment. "
        "Citation precision measures relevance against gold references. Live Qwen results are separate."
    )
    st.dataframe(pd.DataFrame(result["answers"]).T, hide_index=False)
    with st.expander("Benchmark configuration and limitations"):
        st.json(result["configuration"])
        st.write(result["live_generation"])
    records = pd.DataFrame(result["records"])
    method = st.selectbox("Retrieval method", sorted(records["method"].unique()))
    difficulty = st.multiselect(
        "Difficulty",
        sorted(records["difficulty"].unique()),
        default=sorted(records["difficulty"].unique()),
    )
    types = st.multiselect(
        "Question type",
        sorted(records["question_type"].unique()),
        default=sorted(records["question_type"].unique()),
    )
    failures_only = st.checkbox("Only failed cases", True)
    chosen = records[
        (records["method"] == method)
        & records["difficulty"].isin(difficulty)
        & records["question_type"].isin(types)
    ]
    if failures_only:
        chosen = chosen[chosen["failed"]]
    if not chosen.empty:
        grouped = chosen.groupby("question_type").size().reset_index(name="questions")
        st.plotly_chart(
            px.bar(
                grouped,
                x="question_type",
                y="questions",
                title="Selected retrieval failures by question type",
                color_discrete_sequence=["#B7791F"],
            ),
            width="stretch",
        )
        row_id = st.selectbox("Inspect question", chosen["question_id"].tolist())
        row = chosen.loc[chosen["question_id"] == row_id].iloc[0]
        st.write(row["question"])
        st.write("Expected:", row["expected_answer"])
        st.write("Expected references:", row["expected_references"])
        st.json(
            {
                "retrieved": row["retrieved"],
                "prediction": row["prediction"],
                "metrics": row["metrics"],
                "answer_metrics": row["answer_metrics"],
            },
            expanded=False,
        )
    else:
        st.info("No matching cases.")
    st.download_button(
        "Download benchmark JSON", path.read_bytes(), path.name, mime="application/json"
    )
