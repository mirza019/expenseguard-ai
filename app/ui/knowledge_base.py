"""Policy corpus management, provenance inspection, rebuild and grounded policy queries."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from app.rag.answers import grounded_answer
from app.rag.datasets import DEFAULT_ROOT, generate_policies, write_json
from app.rag.index import HashEmbedding, PolicyIndex, SentenceEmbedding, build_index
from app.services.policy_rag import extract_policy

ROOT = Path(__file__).resolve().parents[2]


def _policy_pdf_preview(path: Path, key: str) -> None:
    """Offer an in-app source preview and the original PDF download."""
    _policy_bytes_preview(path.read_bytes(), path.name, key)


def _policy_bytes_preview(content: bytes, filename: str, key: str) -> None:
    """Render one selected page without placing the full PDF in a WebSocket message."""
    with st.expander("View policy PDF"):
        import fitz

        with fitz.open(stream=content, filetype="pdf") as document:
            page_count = document.page_count
            page_number = st.number_input(
                "Page",
                min_value=1,
                max_value=page_count,
                value=1,
                step=1,
                key=key + "_page",
            )
            page = document.load_page(int(page_number) - 1)
            preview = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).tobytes(
                "png"
            )
        st.image(preview, caption=f"{filename} · page {page_number}", width="stretch")
        st.caption(f"Page {page_number} of {page_count}")
    st.download_button(
        "Download policy PDF",
        content,
        filename,
        mime="application/pdf",
        key=key + "_download",
    )


def policy_quick_panel() -> None:
    """Simple policy workflow; the complete context-engineering console remains advanced."""
    st.subheader("Policy evidence")
    st.write(
        "Optionally compare expenses with the policy version that applied on the transaction date. "
        "FinContext AI keeps the document, section, page, and version with every answer."
    )
    with st.expander("Upload governance or policy PDF", expanded=False):
        uploaded_policy = st.file_uploader(
            "Governance PDF", type=["pdf"], key="governance_policy_upload"
        )
        policy_title = st.text_input("Document title", key="governance_policy_title")
        policy_version = st.text_input("Document version", "1.0", key="governance_policy_version")
        policy_effective = st.date_input(
            "Effective from", date.today(), key="governance_policy_effective"
        )
        if st.button(
            "Add governance document",
            disabled=uploaded_policy is None or not policy_title.strip(),
            key="add_governance_policy",
        ):
            try:
                document = extract_policy(
                    uploaded_policy.getvalue(), policy_title, policy_version, policy_effective
                )
                documents = tuple(st.session_state.get("policy_documents", ()))
                if document.document_id in {item.document_id for item in documents}:
                    raise ValueError("This document is already in the library.")
                st.session_state["policy_documents"] = (*documents, document)
                st.session_state["policy_filenames"] = {
                    **st.session_state.get("policy_filenames", {}),
                    document.document_id: uploaded_policy.name,
                }
                st.success("Governance document added with page-level provenance.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    uploaded_documents = tuple(st.session_state.get("policy_documents", ()))
    if uploaded_documents:
        st.markdown("##### Uploaded governance files")
        names = st.session_state.get("policy_filenames", {})
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "File": names.get(item.document_id, item.title + ".pdf"),
                        "Title": item.title,
                        "Version": item.version,
                        "Effective": item.effective_date,
                        "Pages": item.page_count,
                        "Status": "Available for review",
                    }
                    for item in uploaded_documents
                ]
            ),
            hide_index=True,
        )
        selected_upload = st.selectbox(
            "View governance file",
            uploaded_documents,
            format_func=lambda item: f"{item.title} · {item.version}",
            key="view_uploaded_governance",
        )
        _policy_bytes_preview(
            selected_upload.source,
            names.get(selected_upload.document_id, selected_upload.title + ".pdf"),
            "uploaded_governance_pdf",
        )
    if st.button("Load fictional policy demo", type="primary", width="stretch"):
        with st.spinner("Preparing versioned policy evidence…"):
            generate_policies()
            try:
                index = build_index(
                    DEFAULT_ROOT / "policies", ROOT / ".local/rag", HashEmbedding()
                )
            except (ImportError, OSError):
                st.error("The policy demo could not be prepared. Open Advanced for diagnostics.")
                return
            for key in ["audit", "pdf_artifact", "pdf_scoped_audit"]:
                st.session_state.pop(key, None)
            st.session_state["policy_index"] = index
            st.session_state["policy_root"] = DEFAULT_ROOT / "policies"

    index = st.session_state.get("policy_index")
    if index is None:
        st.info(
            "Policy evidence is optional. Load the fictional demo above, or continue with the "
            "standard financial audit without policies."
        )
        st.caption("Your own policy PDFs and technical indexing controls are available in Advanced.")
        return

    document_count = len({chunk.document_id for chunk in index.chunks})
    st.success(f"Policy evidence ready: {document_count} versioned documents indexed with citations.")
    document_ids = list(dict.fromkeys(chunk.document_id for chunk in index.chunks))
    selected_document = st.selectbox(
        "Policy document",
        document_ids,
        key="simple_policy_document",
        help="Select a source document to preview or download.",
    )
    source_root = st.session_state.get("policy_root")
    source_path = (
        Path(source_root) / f"{selected_document}.pdf" if source_root else None
    )
    if source_path and source_path.is_file():
        _policy_pdf_preview(source_path, "simple_policy_pdf")
    question = st.text_input(
        "Ask a policy question",
        "What meal limit applied in Germany in October 2025?",
        key="simple_policy_question",
    )
    with st.expander("Optional transaction context"):
        when = st.date_input("Transaction date", date(2025, 10, 15), key="simple_policy_date")
        region = st.selectbox(
            "Country", ["DE", "FR", "ALL"], key="simple_policy_country"
        )
        scope = st.selectbox(
            "Department",
            ["ALL", "Engineering", "Sales", "Finance", "Operations"],
            key="simple_policy_department",
        )
    if st.button("Find policy answer", key="simple_policy_search", width="stretch"):
        answer = grounded_answer(index, question, when.isoformat(), region, scope)
        st.write(answer["answer"])
        if answer["claims"]:
            st.caption("Sources used")
            for claim in answer["claims"]:
                st.caption(
                    f"{claim['reference']} · version {claim['version']} · page {claim['page']}"
                )
        else:
            st.warning("No applicable cited evidence was found. Review the question or context.")


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
        _policy_pdf_preview(source_path, "advanced_policy_pdf")
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
