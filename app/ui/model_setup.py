"""Startup availability status and explicit one-click model installation."""

import streamlit as st

from app.config import Settings, settings
from app.services.model_manager import DownloadProgress, ModelManager, ModelSetupError, ModelStatus


@st.cache_data(ttl=15, show_spinner=False)
def get_status(config: Settings) -> ModelStatus:
    """Cache only nonfinancial availability metadata, never model downloads."""
    return ModelManager(config).status()


def model_setup_panel() -> ModelStatus | None:
    """Discover the local runtime at startup, while preserving non-AI application access."""
    with st.sidebar:
        st.subheader("Local AI setup")
        try:
            config = settings()
        except ValueError as exc:
            st.error(str(exc))
            st.info("Deterministic Mode — financial auditing works without AI.")
            return None
        status = get_status(config)
        st.caption(f"Configured model: {config.ollama_model}")
        if status.state == "ready":
            st.success(
                "AI Ready — Qwen3 is installed and Ollama is reachable."
                if config.ollama_model.startswith("qwen3:")
                else status.message
            )
        elif status.state == "missing":
            st.warning(status.message)
            st.caption(
                "Optional model download: several GB; reserve at least 6 GB of free disk "
                "space. Internet is required for the first download."
            )
            if st.button("Download & Enable AI", type="primary"):
                bar = st.progress(0.0, text="Preparing model download…")

                def update(event: DownloadProgress) -> None:
                    bar.progress(event.fraction or 0.0, text=event.status)

                try:
                    verified = ModelManager(config).download(update)
                    if verified.state == "ready":
                        get_status.clear()
                        st.rerun()
                except ModelSetupError as exc:
                    bar.empty()
                    st.error(str(exc))
        else:
            st.warning(status.message)
            st.write(
                "macOS: install the Ollama application from https://ollama.com/download, "
                "then launch it. If already installed, open Ollama or run `ollama serve`."
            )
            st.write(
                "Linux: install Ollama using its official instructions, start the service, "
                "then refresh status. No GPU is needed for deterministic audits."
            )
            st.caption(
                "Ollama CLI detected."
                if status.cli_installed
                else "Ollama CLI not found; a reachable loopback service can still be used."
            )
        if st.button("Refresh AI status"):
            get_status.clear()
            st.rerun()
        st.info("Deterministic Mode — financial auditing works without AI.")
        return status
