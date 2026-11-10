"""Explicit local Ollama discovery and user-requested, streaming model installation."""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from ollama import Client

from app.config import Settings


@dataclass(frozen=True)
class ModelStatus:
    state: Literal["ready", "missing", "unavailable"]
    cli_installed: bool
    model: str
    message: str


@dataclass(frozen=True)
class DownloadProgress:
    status: str
    completed: int = 0
    total: int = 0

    @property
    def fraction(self) -> float | None:
        return min(1.0, max(0.0, self.completed / self.total)) if self.total > 0 else None


class ModelSetupError(RuntimeError):
    """Safe setup error without endpoint response details."""


class ModelManager:
    """No network at import or construction; no installation without an explicit call."""

    def __init__(self, config: Settings, client: Client | None = None) -> None:
        self.config = config
        self.client = client or Client(host=config.ollama_url, timeout=config.setup_timeout)
        self.pull_client = client or Client(host=config.ollama_url, timeout=config.timeout)

    def status(self) -> ModelStatus:
        """Check the CLI independently of API reachability and exact model-tag presence."""
        cli_installed = shutil.which("ollama") is not None
        try:
            response = self.client.list()
            names = {model.model for model in response.models}
            if self.config.ollama_model in names:
                # Confirm model metadata can be read, rather than trusting a stale tag alone.
                self.client.show(self.config.ollama_model)
                return ModelStatus(
                    "ready",
                    cli_installed,
                    self.config.ollama_model,
                    "AI Ready — model installed and Ollama reachable.",
                )
            return ModelStatus(
                "missing",
                cli_installed,
                self.config.ollama_model,
                "Model Download Required — Ollama is reachable.",
            )
        except Exception:
            return ModelStatus(
                "unavailable",
                cli_installed,
                self.config.ollama_model,
                "Ollama Unavailable — deterministic auditing remains available.",
            )

    def download(self, progress: Callable[[DownloadProgress], None] | None = None) -> ModelStatus:
        """Pull only after the UI action; recheck to avoid redundant weight downloads."""
        before = self.status()
        if before.state == "ready":
            return before
        if before.state == "unavailable":
            raise ModelSetupError("Start Ollama before downloading the model.")
        try:
            stream = self.pull_client.pull(self.config.ollama_model, stream=True)
            try:
                for event in stream:
                    if progress:
                        progress(
                            DownloadProgress(
                                event.status or "Downloading",
                                event.completed or 0,
                                event.total or 0,
                            )
                        )
            finally:
                close = getattr(stream, "close", None)
                if close:
                    close()
        except KeyboardInterrupt:
            raise ModelSetupError("Model download interrupted. Retry to resume Ollama’s download.")
        except Exception as exc:
            raise ModelSetupError(
                "Model download failed. Check connectivity, free disk space and "
                "the model tag, then retry. Deterministic mode still works."
            ) from exc
        after = self.status()
        if after.state != "ready":
            raise ModelSetupError(
                "Download ended, but the model could not be verified. Refresh "
                "status or retry. Agent Mode remains disabled."
            )
        return after
