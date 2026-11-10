"""Build the Pages companion's fictional report; never uses an LLM or private uploads."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agents.graph import run_audit  # noqa: E402
from app.services.reporting import json_report  # noqa: E402
from app.services.validation import validate  # noqa: E402
from scripts.generate_data import generate  # noqa: E402


def main() -> None:
    frame, _ = generate(1200, 42)
    report = run_audit(validate(frame))["report"]
    target = ROOT / "site" / "demo-report.json"
    target.write_text(json_report(report), encoding="utf-8")
    print("Built fictional Pages demo report; no AI inference or model download.")


if __name__ == "__main__":
    main()
