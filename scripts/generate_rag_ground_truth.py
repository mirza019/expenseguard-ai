import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.rag.datasets import generate_ground_truth  # noqa: E402

if __name__ == "__main__":
    result = generate_ground_truth()
    print("Generated generate_rag_ground_truth reproducibly.")
