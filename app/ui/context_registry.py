"""Human-governed financial context registry UI."""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from app.services.context_registry import ContextAsset, ContextRegistry, seed_default_context


def registry() -> ContextRegistry:
    root = Path(__file__).resolve().parents[2]
    service = ContextRegistry(root / ".local" / "context_registry.json")
    seed_default_context(service)
    return service


def context_registry_panel() -> None:
    service = registry()
    st.subheader("Context Registry")
    st.caption("Versioned definitions remain drafts until a finance owner explicitly approves them.")
    assets = service.list()
    st.dataframe(
        pd.DataFrame([{
            "ID": item.asset_id, "Type": item.asset_type, "Name": item.name,
            "Version": item.version, "Scope": item.business_scope, "Owner": item.owner,
            "Status": item.approval_status, "Effective": item.effective_from,
        } for item in assets]), hide_index=True
    )
    conflicts = service.conflicts()
    if conflicts:
        st.warning(f"{len(conflicts)} unresolved definition conflict(s) require review.")
    with st.expander("Add a context definition"):
        name = st.text_input("Definition name", max_chars=120)
        asset_type = st.selectbox("Context type", ["metric", "glossary", "mapping", "policy", "process"])
        definition = st.text_area("Definition or calculation rule", max_chars=2000)
        owner = st.text_input("Business owner", "Finance", max_chars=120)
        version = st.text_input("Version", "1.0", max_chars=40)
        scope = st.text_input("Business scope", "ALL", max_chars=120)
        source = st.text_input("Source reference", max_chars=300)
        effective = st.date_input("Effective from", date.today())
        if st.button("Save as draft", disabled=not name.strip() or not definition.strip()):
            try:
                service.save(ContextAsset.create(
                    asset_id="context-" + name.casefold().replace(" ", "-")[:80],
                    asset_type=asset_type, name=name.strip(), description=name.strip(),
                    definition=definition.strip(), source_reference=source.strip() or "User-provided context",
                    version=version.strip(), effective_from=effective, business_scope=scope.strip() or "ALL",
                    owner=owner.strip(),
                ))
                st.success("Draft saved. It is not authoritative until approved.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    drafts = [item for item in assets if item.approval_status == "draft"]
    if drafts:
        with st.expander("Review and approve drafts"):
            selected = st.selectbox(
                "Draft",
                drafts,
                key="context_draft_review_v2",
                format_func=lambda item: (
                    f"{item.name} · {item.version}"
                    if isinstance(item, ContextAsset)
                    else "Select a draft"
                ),
            )
            if not isinstance(selected, ContextAsset):
                st.warning("Select the draft again to clear an older browser-session value.")
                return
            st.code(selected.definition)
            reviewer = st.text_input("Approving owner", selected.owner, max_chars=120)
            st.warning("Approval makes this version eligible for workflow use.")
            if st.button("Approve selected definition", disabled=not reviewer.strip()):
                service.approve(selected.asset_id, selected.version, reviewer.strip())
                st.success("Context version approved and audit-stamped.")
                st.rerun()
