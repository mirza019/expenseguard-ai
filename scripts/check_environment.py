"""Dependency/configuration checks with no network, inference or model downloads."""

import argparse
import importlib
import importlib.metadata
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check_dependencies(root: Path = ROOT) -> None:
    """Verify exact distribution versions and runtime imports, detecting a damaged environment."""
    for line in (root / "requirements.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", line)
        if not match:
            raise ValueError("requirements.txt must contain exact version pins.")
        name, expected = match.groups()
        if importlib.metadata.version(name) != expected:
            raise ValueError(f"Dependency version mismatch: {name}.")
    for name in [
        "streamlit",
        "pandas",
        "duckdb",
        "langgraph",
        "langchain_ollama",
        "ollama",
        "pydantic",
        "plotly",
        "openpyxl",
    ]:
        importlib.import_module(name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dependencies-only", action="store_true")
    args = parser.parse_args()
    try:
        check_dependencies()
        if not args.dependencies_only:
            from app.config import settings

            settings()
            if not (ROOT / ".env.example").is_file():
                raise ValueError("Missing .env.example template.")
    except Exception:
        print(
            "Environment check failed. Check exact requirements and the local .env values. "
            "No network or model download was attempted.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
