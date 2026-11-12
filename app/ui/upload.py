"""Data intake, unchanged source preview, and quality feedback."""

from pathlib import Path

import pandas as pd
import streamlit as st

from app.services.ingestion import IngestionError, read_upload
from app.services.validation import ValidatedData, validate

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "synthetic_expenses.csv"
LARGE_SAMPLE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "synthetic"
    / "expenses"
    / "transactions_60000.xlsx"
)
STANDARD_SAMPLE = LARGE_SAMPLE.with_name("transactions.csv")


def upload_panel() -> ValidatedData | None:
    """Replace current dataset atomically; invalidate results on each successful load."""
    st.markdown("#### 1. Choose expense data")
    st.caption(
        "CSV or XLSX · maximum 10 MB / 100,000 rows · Excel expands to 100 MB maximum · "
        "EUR only · dates as YYYY-MM-DD"
    )
    uploaded = st.file_uploader(
        "Upload expense file",
        type=["csv", "xlsx"],
        key="expense_file_upload_v2",
        help="Your source file is preserved unchanged. FinContext AI creates a separate normalized analytical copy.",
    )
    st.markdown("##### Quick-load local demonstration data")
    local_standard, local_large = st.columns(2)
    use_standard_sample = local_standard.button(
        "Load transactions.csv",
        disabled=not STANDARD_SAMPLE.exists(),
        help="Loads the local transaction sample without using the browser upload connection.",
        width="stretch",
    )
    use_large_sample = local_large.button(
        "Load 60,000-row workbook",
        disabled=not LARGE_SAMPLE.exists(),
        help="Loads the local 60,000-row workbook without using the browser upload connection.",
        width="stretch",
    )
    st.caption("These options bypass browser transfer and are recommended for the included demo files.")
    primary, demo = st.columns(2)
    use_upload = primary.button(
        "Use uploaded file", disabled=uploaded is None, type="primary", width="stretch"
    )
    sample = demo.button("Try fictional sample", width="stretch")
    if sample or use_upload or use_standard_sample or use_large_sample:
        try:
            if sample:
                source = SAMPLE
                frame = read_upload(source.read_bytes(), source.name)
                source_name = source.name
            elif use_standard_sample:
                frame = read_upload(STANDARD_SAMPLE.read_bytes(), STANDARD_SAMPLE.name)
                source_name = STANDARD_SAMPLE.name
            elif use_large_sample:
                frame = read_upload(LARGE_SAMPLE.read_bytes(), LARGE_SAMPLE.name)
                source_name = LARGE_SAMPLE.name
            else:
                frame = read_upload(uploaded.getvalue(), uploaded.name)
                source_name = uploaded.name
            candidate = validate(frame)
            st.session_state["data"] = candidate
            st.session_state["data_source"] = {
                "name": source_name,
                "format": Path(source_name).suffix.lower().lstrip(".").upper(),
                "rows": len(candidate.original),
            }
            st.session_state.pop("audit", None)
            st.session_state.pop("individual", None)
            for key in [
                "pdf_artifact",
                "pdf_scoped_audit",
                "pdf_start",
                "pdf_end",
                "pdf_preview",
                "analysis_start",
                "analysis_end",
                "analysis_scope_key",
            ]:
                st.session_state.pop(key, None)
        except (IngestionError, ValueError) as exc:
            # Preserve the previous validated dataset, but clearly identify the failure.
            st.error(str(exc))
            st.warning("New file was not loaded. Any displayed dataset is the previous one.")
    with st.expander("Need the larger policy demonstration?"):
        load_policy_demo = st.button("Load 2,400-transaction policy demo")
    if load_policy_demo:
        from app.rag.datasets import generate_expenses

        demo, _ = generate_expenses()
        st.session_state["data"] = validate(demo)
        st.session_state["data_source"] = {
            "name": "fictional-policy-demo",
            "format": "GENERATED",
            "rows": len(demo),
        }
        for key in [
            "audit",
            "pdf_artifact",
            "pdf_scoped_audit",
            "pdf_start",
            "pdf_end",
            "analysis_start",
            "analysis_end",
            "analysis_scope_key",
        ]:
            st.session_state.pop(key, None)
    data = st.session_state.get("data")
    if data is None:
        st.info("Upload your expense export, or try the fictional sample to explore the workflow.")
        return None
    st.success(
        f"Data ready: {len(data.original):,} source rows · "
        f"{len(data.eligible):,} eligible for financial analysis · EUR"
    )
    source = st.session_state.get("data_source")
    if source:
        st.caption(
            f"Loaded file: {source['name']} · {source['format']} · {source['rows']:,} rows"
        )
    if len(data.original) > 10_000:
        st.info(
            "Large-file mode is active. The full dataset is loaded for analysis; "
            "interactive row previews are skipped."
        )
        return data
    with st.expander("Original uploaded data — unchanged", expanded=False):
        st.caption(
            "Previewing the first 25 rows. The complete source remains available to the audit."
        )
        st.dataframe(data.original.head(25), hide_index=True)
    with st.expander("Data quality and transformations"):
        st.write(data.transformations)
        if data.issues:
            st.dataframe(pd.DataFrame([f.model_dump() for f in data.issues]), hide_index=True)
        else:
            st.success("No data-quality issues detected.")
    return data
