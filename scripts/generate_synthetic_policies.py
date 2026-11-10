import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.rag.datasets import generate_policies  # noqa: E402

if __name__ == "__main__":
    result = generate_policies()
    print("Generated generate_synthetic_policies reproducibly.")
