import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.rag.datasets import DEFAULT_ROOT  # noqa: E402
from app.rag.index import HashEmbedding, SentenceEmbedding, build_index  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding", default="hash")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / ".local/rag")
    args = parser.parse_args()
    embedding = (
        HashEmbedding()
        if args.embedding == "hash"
        else SentenceEmbedding(args.embedding, args.allow_download)
    )
    index = build_index(DEFAULT_ROOT / "policies", args.output, embedding)
    print(
        f"Indexed {len(index.chunks)} chunks with {embedding.name}; no evaluation labels indexed."
    )
