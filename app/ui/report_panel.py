"""PDF report options, optional policy sources, validated preview and session-local caching."""

import base64
from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app.services.policy_rag import extract_policy
from app.services.report_validation import ReportValidationError, report_key, select_period
from app.services.reporting import pdf_report
from app.services.validation import ValidatedData


def pdf_report_panel(data: ValidatedData, audit: dict) -> None:
    """Generate only on explicit action; downloads reuse the retained PDF bytes."""
    st.subheader("Generate Audit Report")
    if len(audit.get("results", {})) != 4:
        st.info("Run the complete audit before generating a PDF.")
        st.session_state.pop("pdf_artifact", None)
        return
    dates = data.cleaned["date"].dropna()
    if dates.empty:
        st.warning("PDF period selection requires at least one dated transaction.")
        return
    low, high = dates.min().date(), dates.max().date()
    left, right = st.columns(2)
    start = left.date_input(
        "Reporting period start", low, min_value=low, max_value=high, key="pdf_start"
    )
    end = right.date_input(
        "Reporting period end", high, min_value=low, max_value=high, key="pdf_end"
    )
    include_ai = st.checkbox("Include verified AI-selected investigation actions", key="pdf_ai")
    st.caption(
        "Financial facts always come from deterministic tools. This option uses existing "
        "verified agent actions; no model request is made during PDF rendering."
    )
    with st.expander("Optional financial policy PDFs"):
        st.caption(
            "Text-based PDFs only. Title, version and effective date are uploader-declared. "
            "Policies remain in memory. Automatic checks support explicit category limits; "
            "other clauses require human review."
        )
        upload = st.file_uploader("Policy PDF", type=["pdf"], key="policy_upload")
        title = st.text_input("Policy document title", max_chars=200)
        version = st.text_input("Policy version", max_chars=80)
        effective = st.date_input("Policy effective date", value=low)
        if st.button("Add policy document", disabled=upload is None):
            try:
                documents = tuple(st.session_state.get("policy_documents", ()))
                if len(documents) >= 5:
                    raise ValueError(
                        "Maximum five policy documents per session. Clear before adding more."
                    )
                document = extract_policy(upload.getvalue(), title, version, effective)
                if document.document_id in {d.document_id for d in documents}:
                    raise ValueError("This policy document is already registered.")
                st.session_state["policy_documents"] = (*documents, document)
                st.success(
                    f"Added {document.title}, version {document.version}: {document.page_count} pages."
                )
            except ValueError as exc:
                st.error(str(exc))
        if st.session_state.get("policy_documents"):
            st.write(
                [
                    f"{d.title} / {d.version} / effective {d.effective_date}"
                    for d in st.session_state["policy_documents"]
                ]
            )
            if st.button("Clear policy documents"):
                st.session_state["policy_documents"] = ()
                st.session_state.pop("pdf_artifact", None)
                st.rerun()
    policies = tuple(st.session_state.get("policy_documents", ()))
    key = report_key(data, audit, start, end, include_ai, policies)
    artifact = st.session_state.get("pdf_artifact")
    if artifact and artifact["key"] != key:
        st.session_state.pop("pdf_artifact", None)
        artifact = None
    if start > end:
        st.error("Reporting period start must not follow its end.")
        return
    scoped_data, scoped_audit = data, audit
    if (start, end) != (low, high):
        st.info(
            "A narrower period requires a fresh deterministic audit. Its findings are shown "
            "below and used unchanged in the PDF. Full-upload dashboard totals remain separate."
        )
        scoped_key = report_key(data, audit, start, end, False)
        cached = st.session_state.get("pdf_scoped_audit")
        if st.button("Prepare selected-period audit"):
            from app.agents.graph import run_audit

            try:
                scoped = select_period(data, start, end)
                cached = {
                    "key": scoped_key,
                    "data": scoped,
                    "audit": run_audit(
                        scoped,
                        policy_index=audit.get("policy_index"),
                        policy_root=audit.get("policy_root"),
                    ),
                }
                st.session_state["pdf_scoped_audit"] = cached
            except ReportValidationError as exc:
                st.error(str(exc))
        if not cached or cached["key"] != scoped_key:
            return
        scoped_data, scoped_audit = cached["data"], cached["audit"]
        st.write("Verified selected-period findings")
        st.dataframe(pd.DataFrame(scoped_audit["report"]["findings"]), hide_index=True)
    if st.button("Generate PDF Audit Report", type="primary"):
        try:
            with st.spinner("Reconciling audit and policy evidence; composing PDF…"):
                verified, content = pdf_report(
                    scoped_data, scoped_audit, start, end, include_ai, policies
                )
            artifact = {
                "key": key,
                "bytes": content,
                "report": verified,
                "filename": f"FinContext_AI_Audit_Report_{date.today().isoformat()}.pdf",
            }
            st.session_state["pdf_artifact"] = artifact
        except ValueError as exc:
            st.session_state.pop("pdf_artifact", None)
            st.error(f"PDF validation failed: {exc}")
            return
        except Exception:
            st.session_state.pop("pdf_artifact", None)
            st.error(
                "PDF rendering failed. Review the source text and retry; no report was issued."
            )
            return
    if artifact:
        st.success(
            f"PDF ready: {artifact['report'].analysis_mode}; "
            f"{len(artifact['report'].findings)} verified financial findings."
        )
        st.download_button(
            "Download PDF Audit Report",
            artifact["bytes"],
            artifact["filename"],
            mime="application/pdf",
            key="download_pdf",
        )
        if st.checkbox("Preview generated PDF", key="pdf_preview"):
            if len(artifact["bytes"]) <= 8 * 1024 * 1024:
                encoded = base64.b64encode(artifact["bytes"]).decode("ascii")
                components.html(
                    '<object data="data:application/pdf;base64,'
                    + encoded
                    + '" type="application/pdf" width="100%" height="760">'
                    "Your browser cannot preview this PDF. Use Download PDF Audit Report above."
                    "</object>",
                    height=780,
                    scrolling=True,
                )
            else:
                st.info("Large report: use the download button to view it in your PDF reader.")
