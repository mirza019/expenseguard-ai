"""Data intake, unchanged source preview, and quality feedback."""

from pathlib import Path

import pandas as pd
import streamlit as st

from app.services.ingestion import IngestionError, read_upload
from app.services.validation import ValidatedData, validate

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "synthetic_expenses.csv"


def upload_panel() -> ValidatedData | None:
    """Replace current dataset atomically; invalidate results on each successful load."""
    st.subheader("Upload expense records")
    st.caption("CSV or XLSX · maximum 10 MB / 100,000 rows · EUR only · ISO dates YYYY-MM-DD")
    uploaded = st.file_uploader("Expense file", type=["csv", "xlsx"])
    sample = st.button("Load fictional sample dataset")
    use_upload = st.button("Validate uploaded file", disabled=uploaded is None)
    if sample or use_upload:
        try:
            frame = (
                read_upload(SAMPLE.read_bytes(), SAMPLE.name)
                if sample
                else read_upload(uploaded.getvalue(), uploaded.name)
            )
            candidate = validate(frame)
            st.session_state["data"] = candidate
            st.session_state.pop("audit", None)
            st.session_state.pop("individual", None)
            for key in ["pdf_artifact", "pdf_scoped_audit", "pdf_start", "pdf_end", "pdf_preview"]:
                st.session_state.pop(key, None)
        except (IngestionError, ValueError) as exc:
            # Preserve the previous validated dataset, but clearly identify the failure.
            st.error(str(exc))
            st.warning("New file was not loaded. Any displayed dataset is the previous one.")
    data = st.session_state.get("data")
    if data is None:
        st.info("Load the fictional sample or upload a file to begin.")
        return None
    st.success(
        f"Current dataset: {len(data.original):,} source rows; "
        f"{len(data.eligible):,} financially eligible rows. Currency: EUR."
    )
    with st.expander("Original uploaded data — unchanged", expanded=False):
        st.dataframe(data.original.head(100), hide_index=True)
    with st.expander("Data quality and transformations"):
        st.write(data.transformations)
        if data.issues:
            st.dataframe(pd.DataFrame([f.model_dump() for f in data.issues]), hide_index=True)
        else:
            st.success("No data-quality issues detected.")
    return data
