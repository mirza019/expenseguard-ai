import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.evaluation.benchmark import evaluate  # noqa: E402
from app.rag.datasets import DEFAULT_ROOT, write_json  # noqa: E402
from app.rag.index import HashEmbedding, PolicyIndex, SentenceEmbedding  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["development", "test"], default="test")
    parser.add_argument("--index", type=Path, default=ROOT / ".local/rag")
    parser.add_argument("--embedding", default="hash")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "data/evaluation/results/latest.json")
    args = parser.parse_args()
    embedding = HashEmbedding() if args.embedding == "hash" else SentenceEmbedding(args.embedding)
    index = PolicyIndex.load(args.index, embedding)
    questions = [
        json.loads(line)
        for line in (DEFAULT_ROOT / "ground_truth/questions.jsonl").read_text().splitlines()
    ]
    results = evaluate(index, questions, args.split, args.live)
    write_json(args.output, results)
    print(json.dumps({k: v for k, v in results.items() if k not in ["records"]}, indent=2))
