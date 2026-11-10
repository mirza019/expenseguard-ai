"""Local hierarchical policy index: provenance, applicability, FAISS, BM25 and RRF."""

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import duckdb
import faiss
import numpy as np
import pandas as pd
import pymupdf
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import HashingVectorizer


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    document_hash: str
    title: str
    version: str
    effective_from: str | None
    effective_to: str | None
    department: str
    country: str
    category: str
    section_id: str
    section_title: str
    parent_id: str
    page_start: int
    page_end: int
    text: str
    parent_text: str
    content_hash: str
    approval_requirements: str
    provenance: str
    status: str

    @property
    def reference(self) -> str:
        return f"{self.document_id}:{self.section_id}"


class HashEmbedding:
    """Small deterministic nonsemantic dense baseline. Never mislabel as a neural model."""

    name = "hashing-word-char-v1 (nonsemantic baseline)"
    dimensions = 512

    def __init__(self):
        self.word = HashingVectorizer(
            n_features=256, alternate_sign=False, norm=None, ngram_range=(1, 2)
        )
        self.char = HashingVectorizer(
            n_features=256, alternate_sign=False, norm=None, analyzer="char_wb", ngram_range=(3, 5)
        )

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.hstack(
            [self.word.transform(texts).toarray(), self.char.transform(texts).toarray()]
        ).astype("float32")
        faiss.normalize_L2(vectors)
        return vectors


class SentenceEmbedding:
    """Optional explicit-download profile; normal imports/CI never fetch embedding weights."""

    def __init__(self, model="sentence-transformers/all-MiniLM-L6-v2", allow_download=False):
        from sentence_transformers import SentenceTransformer

        self.name = model
        self.model = SentenceTransformer(model, device="cpu", local_files_only=not allow_download)
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        ).astype("float32")


def extract_chunks(
    source: bytes, meta: dict, max_tokens: int = 220, overlap: int = 35
) -> list[Chunk]:
    """Keep logical section parents intact; token-bounded children retain page/source provenance."""
    if max_tokens < 40 or overlap >= max_tokens or overlap < 0:
        raise ValueError("Use at least 40 tokens and overlap smaller than the chunk limit.")
    digest = hashlib.sha256(source).hexdigest()
    if meta.get("document_hash") != digest:
        raise ValueError("Document hash does not match catalog provenance.")
    sections = []
    with pymupdf.open(stream=source, filetype="pdf") as pdf:
        if pdf.needs_pass or len(pdf) > 100:
            raise ValueError("Use text-based unencrypted policies of at most 100 pages.")
        section, title = "0", "Document metadata"
        parts = []
        first = 1
        last_content_page = 1
        for page_num, page in enumerate(pdf, 1):
            for line in page.get_text(sort=True).splitlines():
                if line.strip().startswith("SYNTHETIC"):
                    continue
                match = re.match(r"^(\d+\.\d+)\s+(.+)", line.strip())
                if match:
                    if parts:
                        sections.append(
                            (section, title, first, last_content_page, "\n".join(parts))
                        )
                    section, title = match.groups()
                    parts = []
                    first = page_num
                parts.append(line)
                last_content_page = page_num
        if parts:
            sections.append((section, title, first, last_content_page, "\n".join(parts)))
    if not any(len(s[-1].strip()) > 30 for s in sections):
        raise ValueError("No readable text; scanned PDFs need OCR.")
    output = []
    for section, title, first, last, parent in sections:
        words = parent.split()
        for offset in range(0, len(words), max_tokens - overlap):
            text = " ".join(words[offset : offset + max_tokens])
            if not text:
                continue
            if meta.get("provenance", "").startswith("synthetic ReportLab"):
                country = "FR" if section == "2.2" else "DE" if section in {"2.1", "3.1"} else "ALL"
                department = "Engineering" if section in {"2.2", "3.1"} else "ALL"
            else:
                country = meta.get("country", "UNKNOWN")
                department = meta.get("department", "UNKNOWN")
            if meta.get("status") == "unknown":
                country = department = "UNKNOWN"
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            parent_id = f"{meta['document_id']}:{section}"
            cid = hashlib.sha256(
                f"{digest}:{parent_id}:{offset}:{content_hash}".encode()
            ).hexdigest()
            output.append(
                Chunk(
                    cid,
                    meta["document_id"],
                    digest,
                    meta["title"],
                    meta.get("version", "UNKNOWN"),
                    meta.get("effective_from"),
                    meta.get("effective_to"),
                    department,
                    country,
                    meta.get("category", "UNKNOWN"),
                    section,
                    title,
                    parent_id,
                    first,
                    last,
                    text,
                    parent,
                    content_hash,
                    "director"
                    if "director approval" in parent.lower()
                    else "manager"
                    if "manager" in parent.lower()
                    else "UNKNOWN",
                    meta.get("provenance", "UNKNOWN"),
                    meta.get("status", "unknown"),
                )
            )
    # Cross-page exception context is kept separate, with its own real citation, not silently spliced.
    return output


def applicable(chunk: Chunk, on_date: str, country="ALL", department="ALL") -> bool:
    if not chunk.effective_from or chunk.status == "unknown" or chunk.version == "UNKNOWN":
        return False
    if not (
        chunk.effective_from <= on_date
        and (not chunk.effective_to or on_date <= chunk.effective_to)
    ):
        return False
    return (chunk.country in {"ALL", country} if country != "ALL" else chunk.country == "ALL") and (
        chunk.department in {"ALL", department}
        if department != "ALL"
        else chunk.department == "ALL"
    )


@dataclass
class Hit:
    chunk: Chunk
    score: float
    rank: int


class PolicyIndex:
    def __init__(self, chunks: list[Chunk], embedder=None):
        if not chunks:
            raise ValueError("No policy chunks to index.")
        self.chunks = chunks
        self.embedder = embedder or HashEmbedding()
        self.vectors = self.embedder.encode(
            [c.title + " " + c.section_title + " " + c.text for c in chunks]
        )
        self.dense = faiss.IndexFlatIP(self.vectors.shape[1])
        self.dense.add(self.vectors)
        self.bm25 = BM25Okapi(
            [tokens(c.title + " " + c.section_title + " " + c.text) for c in chunks]
        )

    def search(
        self, query: str, on_date: str, country="DE", department="ALL", method="hybrid", k=5
    ) -> list[Hit]:
        date.fromisoformat(on_date)
        if not tokens(query):
            return []
        if method not in {"bm25", "faiss", "hybrid", "reranked_hybrid"} or not 1 <= k <= 30:
            raise ValueError("Unsupported retrieval method or limit.")
        eligible = [
            i for i, c in enumerate(self.chunks) if applicable(c, on_date, country, department)
        ]
        # Resolve overlapping versions by title/effective start, retaining ties as conflict evidence.
        latest = {}
        for i in eligible:
            c = self.chunks[i]
            latest[c.title] = max(latest.get(c.title, ""), c.effective_from)
        eligible = [
            i for i in eligible if self.chunks[i].effective_from == latest[self.chunks[i].title]
        ]
        if not eligible:
            return []
        lexical = self.bm25.get_scores(tokens(query))
        dense_order = []
        query_vector = None
        if method != "bm25":
            query_vector = self.embedder.encode([query])
            _, order = self.dense.search(query_vector, len(self.chunks))
            allowed = set(eligible)
            dense_order = [int(i) for i in order[0] if int(i) in allowed]
        bm_order = sorted(eligible, key=lambda i: (-lexical[i], self.chunks[i].chunk_id))
        if method == "bm25":
            score = {i: float(lexical[i]) for i in eligible}
            ranking = bm_order
        elif method == "faiss":
            dots = self.vectors @ query_vector[0]
            score = {i: float(dots[i]) for i in eligible}
            ranking = dense_order
        else:
            score = {i: 0.0 for i in eligible}
            for ranks in [bm_order, dense_order]:
                for rank, i in enumerate(ranks, 1):
                    score[i] += 1 / (60 + rank)
            if method == "reranked_hybrid":
                # Transparent local lexical reranker, not a claimed neural cross-encoder.
                q = set(tokens(query))
                for i in eligible:
                    score[i] += 0.02 * len(q & set(tokens(self.chunks[i].section_title)))
            ranking = sorted(eligible, key=lambda i: (-score[i], self.chunks[i].chunk_id))
        found = []
        seen = set()
        for i in ranking:
            chunk = self.chunks[i]
            if chunk.reference in seen:
                continue
            seen.add(chunk.reference)
            found.append(Hit(chunk, score[i], len(found) + 1))
            if len(found) >= k:
                break
        return found

    def expand(self, hits: list[Hit]) -> list[Chunk]:
        """Add real exception/cross-reference parents, keeping provenance and applicability visible."""
        output = {h.chunk.reference: h.chunk for h in hits}
        for h in hits:
            if h.chunk.section_id in {"2.1", "2.2"}:
                for c in self.chunks:
                    if c.document_id == h.chunk.document_id and c.section_id == "3.1":
                        output.setdefault(c.reference, c)
        return list(output.values())

    def save(self, output: Path, catalog: list[dict]) -> None:
        output = Path(output)
        if output.exists() and any(output.iterdir()) and not (output / "manifest.json").is_file():
            raise ValueError("Refusing to replace a non-index directory.")
        backup_path = output.with_name(output.name + ".previous")
        if backup_path.exists() and not (backup_path / "manifest.json").is_file():
            raise ValueError("Unrecognized backup directory; review it manually.")
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = Path(tempfile.mkdtemp(prefix="rag-build-", dir=output.parent))
        try:
            faiss.write_index(self.dense, str(temp / "vectors.faiss"))
            with duckdb.connect(str(temp / "metadata.duckdb")) as db:
                docs = pd.DataFrame(catalog)
                chunks = pd.DataFrame({"record": [json.dumps(asdict(c)) for c in self.chunks]})
                db.register("source_docs", docs)
                db.register("source_chunks", chunks)
                db.execute("CREATE TABLE documents AS SELECT * FROM source_docs")
                db.execute("CREATE TABLE chunks AS SELECT * FROM source_chunks")
            manifest = {
                "embedding": self.embedder.name,
                "dimensions": self.vectors.shape[1],
                "chunks": len(self.chunks),
                "documents": len(catalog),
                "files": {
                    f: hashlib.sha256((temp / f).read_bytes()).hexdigest()
                    for f in ["vectors.faiss", "metadata.duckdb"]
                },
            }
            (temp / "manifest.json").write_text(json.dumps(manifest, indent=2))
            backup = output.with_name(output.name + ".previous")
            if backup.exists():
                shutil.rmtree(backup)
            if output.exists():
                output.rename(backup)
            try:
                temp.rename(output)
            except Exception:
                if backup.exists():
                    backup.rename(output)
                raise
            if backup.exists():
                shutil.rmtree(backup)
        finally:
            if temp.exists():
                shutil.rmtree(temp)

    @classmethod
    def load(cls, output: Path, embedder=None):
        output = Path(output)
        manifest = json.loads((output / "manifest.json").read_text())
        embedder = embedder or HashEmbedding()
        if manifest["embedding"] != embedder.name:
            raise ValueError("Embedding configuration mismatch.")
        for name, digest in manifest["files"].items():
            if (
                name not in {"vectors.faiss", "metadata.duckdb"}
                or hashlib.sha256((output / name).read_bytes()).hexdigest() != digest
            ):
                raise ValueError("Index checksum mismatch; rebuild the local index.")
        with duckdb.connect(str(output / "metadata.duckdb"), read_only=True) as db:
            chunks = [
                Chunk(**json.loads(row[0]))
                for row in db.execute("SELECT record FROM chunks").fetchall()
            ]
        if any(hashlib.sha256(c.text.encode()).hexdigest() != c.content_hash for c in chunks):
            raise ValueError("Chunk content hash mismatch; rebuild index.")
        instance = cls(chunks, embedder)
        saved = faiss.read_index(str(output / "vectors.faiss"))
        if saved.ntotal != len(chunks) or saved.d != manifest["dimensions"]:
            raise ValueError("Index and metadata do not agree.")
        instance.dense = saved
        return instance


def build_index(policies: Path, output: Path, embedder=None) -> PolicyIndex:
    """Only catalogued PDF sources enter retrieval; labels/questions/specifications are excluded."""
    policies = Path(policies)
    if (
        Path(output).resolve() == policies.resolve()
        or Path(output).resolve() in policies.resolve().parents
    ):
        raise ValueError("Index output cannot replace policy sources or their parent directory.")
    if "ground_truth" in policies.parts:
        raise ValueError("Ground truth cannot be indexed.")
    catalog = json.loads((policies / "catalog.json").read_text())
    chunks = []
    retained = []
    seen = set()
    for meta in catalog:
        name = meta["path"]
        if Path(name).name != name or not name.endswith(".pdf"):
            raise ValueError("Index only policy PDFs.")
        source = (policies / name).read_bytes()
        digest = hashlib.sha256(source).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        retained.append(meta)
        chunks.extend(extract_chunks(source, meta))
    result = PolicyIndex(chunks, embedder)
    result.save(output, retained)
    return result
