"""Policy corpus management, provenance inspection, rebuild and grounded policy queries."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from app.rag.answers import grounded_answer
from app.rag.datasets import DEFAULT_ROOT, generate_policies, write_json
from app.rag.index import HashEmbedding, PolicyIndex, SentenceEmbedding, build_index

ROOT = Path(__file__).resolve().parents[2]


def knowledge_base() -> None:
    st.subheader("Policy Knowledge Base")
    st.caption(
        "Applicable versions, source pages and inspectable context. Unknown metadata is never guessed."
    )
    profile = st.selectbox(
        "Embedding profile",
        ["Deterministic baseline (no downloads)", "SentenceTransformer (cached model)"],
    )

    def embedding():
        return HashEmbedding() if profile.startswith("Deterministic") else SentenceEmbedding()

    if st.button("Load / rebuild synthetic policy corpus"):
        with st.spinner("Generating fictional PDFs and indexing policy-only content…"):
            generate_policies()
            try:
                index = build_index(DEFAULT_ROOT / "policies", ROOT / ".local/rag", embedding())
            except (ImportError, OSError):
                st.error(
                    "Optional embedding model unavailable. Use the baseline or explicitly prepare the neural profile via the CLI."
                )
                return
            for key in ["audit", "pdf_artifact", "pdf_scoped_audit"]:
                st.session_state.pop(key, None)
            st.session_state["policy_index"] = index
            st.session_state["policy_root"] = DEFAULT_ROOT / "policies"
    if st.button("Load existing local index"):
        try:
            st.session_state["policy_index"] = PolicyIndex.load(ROOT / ".local/rag", embedding())
            st.session_state["policy_root"] = DEFAULT_ROOT / "policies"
        except (ValueError, OSError, RuntimeError):
            st.error("Index unavailable or inconsistent. Rebuild it first.")
    with st.expander("Upload a policy PDF and declare metadata"):
        upload = st.file_uploader("Knowledge-base PDF", type=["pdf"], key="kb_pdf")
        title = st.text_input("Document title", key="kb_title")
        version = st.text_input("Document version", key="kb_version")
        effective = st.date_input("Effective from", date(2025, 1, 1))
        country = st.selectbox("Policy country", ["UNKNOWN", "DE", "FR", "ALL"])
        department = st.selectbox(
            "Policy department", ["UNKNOWN", "ALL", "Engineering", "Sales", "Finance", "Operations"]
        )
        category = st.text_input("Expense category", key="kb_category")
        if st.button("Validate and index uploaded policy", disabled=upload is None):
            try:
                from app.services.policy_rag import extract_policy

                checked = extract_policy(upload.getvalue(), title, version, effective)
                target = ROOT / ".local/user_policies"
                target.mkdir(parents=True, exist_ok=True)
                catalog_path = target / "catalog.json"
                catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else []
                if checked.document_id in {d["document_hash"] for d in catalog}:
                    raise ValueError("Duplicate PDF already indexed.")
                doc_id = "uploaded-" + checked.document_id[:16]
                (target / (doc_id + ".pdf")).write_bytes(checked.source)
                catalog.append(
                    dict(
                        document_id=doc_id,
                        path=doc_id + ".pdf",
                        document_hash=checked.document_id,
                        title=title,
                        version=version,
                        effective_from=effective.isoformat(),
                        effective_to=None,
                        country=country,
                        department=department,
                        category=category or "UNKNOWN",
                        status="active",
                        provenance="uploader-declared metadata; text extracted by PyMuPDF",
                    )
                )
                write_json(catalog_path, catalog)
                st.session_state["policy_index"] = build_index(target, ROOT / ".local/user_rag")
                st.session_state["policy_root"] = target
            except ValueError as exc:
                st.error(str(exc))
    index = st.session_state.get("policy_index")
    if index is None:
        st.info(
            "Load the synthetic corpus or index your own text-based policy PDF. Financial auditing works without it."
        )
        return
    meta = pd.DataFrame(
        [
            {
                "document": c.document_id,
                "title": c.title,
                "version": c.version,
                "effective": c.effective_from or "UNKNOWN",
                "country": c.country,
                "department": c.department,
                "section": c.section_id,
                "pages": f"{c.page_start}–{c.page_end}",
                "status": c.status,
            }
            for c in index.chunks
        ]
    )
    st.metric("Indexed policy documents", meta["document"].nunique())
    st.dataframe(meta.drop_duplicates(), hide_index=True)
    selected = st.selectbox(
        "Inspect section", list(dict.fromkeys(c.reference for c in index.chunks))
    )
    chunk = next(c for c in index.chunks if c.reference == selected)
    with st.expander("Section and child-chunk context"):
        st.write(chunk.parent_text)
        st.json(
            {
                "parent_id": chunk.parent_id,
                "chunk_id": chunk.chunk_id,
                "document_hash": chunk.document_hash,
                "content_hash": chunk.content_hash,
                "provenance": chunk.provenance,
            },
            expanded=False,
        )
    source_root = st.session_state.get("policy_root")
    source_path = Path(source_root) / (chunk.document_id + ".pdf") if source_root else None
    if source_path and source_path.is_file():
        st.download_button(
            "Download selected policy source",
            source_path.read_bytes(),
            source_path.name,
            mime="application/pdf",
        )
    st.subheader("Ask an evidence-grounded policy question")
    query = st.text_input("Policy question", "What meal limit applies in Germany in October 2025?")
    when = st.date_input("Transaction date", date(2025, 10, 15))
    region = st.selectbox("Transaction country", ["DE", "FR", "ALL"])
    scope = st.selectbox(
        "Transaction department", ["ALL", "Engineering", "Sales", "Finance", "Operations"]
    )
    if st.button("Retrieve applicable evidence"):
        answer = grounded_answer(index, query, when.isoformat(), region, scope)
        st.write(answer["answer"])
        st.write("Evidence status:", answer["behavior"])
        for claim in answer["claims"]:
            st.caption(f"{claim['reference']} · version {claim['version']} · page {claim['page']}")
