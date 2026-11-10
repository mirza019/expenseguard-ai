"""In-memory, page-aware policy retrieval; no embeddings or model downloads."""

import hashlib
import re
from dataclasses import dataclass
from datetime import date

import pymupdf
from pydantic import BaseModel, ConfigDict

from app.services.validation import ValidatedData, cents


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    page: int
    section: str
    text: str


@dataclass(frozen=True)
class PolicyDocument:
    document_id: str
    title: str
    version: str
    effective_date: date
    page_count: int
    chunks: tuple[PolicyChunk, ...]
    source: bytes


class PolicyCitation(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    document_id: str
    chunk_id: str
    title: str
    version: str
    effective_date: date
    page: int
    section: str
    quote: str
    source_row: int
    transaction_id: str
    assessment: str
    explanation: str
    threshold_cents: int | None = None
    observed_cents: int


def extract_policy(source: bytes, title: str, version: str, effective_date: date) -> PolicyDocument:
    """Extract textual PDFs into overlapping same-page/section chunks with source hashes."""
    if not title.strip() or not version.strip() or len(title) > 200 or len(version) > 80:
        raise ValueError("Supply a policy title and version (maximum 200/80 characters).")
    if not source or len(source) > 10 * 1024 * 1024:
        raise ValueError("Policy PDFs must be nonempty and at most 10 MB.")
    digest = hashlib.sha256(source).hexdigest()
    chunks = []
    try:
        with pymupdf.open(stream=source, filetype="pdf") as pdf:
            if pdf.needs_pass or not 1 <= len(pdf) <= 100:
                raise ValueError("Use an unencrypted policy PDF of 1–100 pages.")
            section = "Unnumbered section"
            total = 0
            for page_number, page in enumerate(pdf, 1):
                text = page.get_text(sort=True)
                total += len(text)
                if total > 500_000:
                    raise ValueError("Policy text exceeds the 500,000-character limit.")
                blocks = []
                current = []
                for line in text.splitlines():
                    if re.match(r"^\d+(?:\.\d+)*[.)]?\s+\S", line.strip()):
                        if current:
                            blocks.append((section, "\n".join(current)))
                            current = []
                        section = line.strip()
                    current.append(line)
                if current:
                    blocks.append((section, "\n".join(current)))
                for section_id, block in blocks:
                    for offset in range(0, len(block), 1250):
                        passage = block[offset : offset + 1400].strip()
                        if passage:
                            cid = hashlib.sha256(
                                f"{digest}:{page_number}:{section_id}:{offset}:{passage}".encode()
                            ).hexdigest()
                            chunks.append(PolicyChunk(cid, page_number, section_id, passage))
            pages = len(pdf)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Cannot read this policy PDF. Use a valid text-based PDF.") from exc
    if not chunks:
        raise ValueError("No extractable policy text. Scanned PDFs need OCR before upload.")
    return PolicyDocument(
        digest, title.strip(), version.strip(), effective_date, pages, tuple(chunks), source
    )


def retrieve(
    documents: tuple[PolicyDocument, ...], query: str, on_date: date, limit: int = 2
) -> list[tuple[PolicyDocument, PolicyChunk]]:
    """Lexical retrieval with effective-date/latest-version filtering and stable ranking."""
    tokens = set(re.findall(r"[a-z]{3,}", query.lower()))
    eligible = [d for d in documents if d.effective_date <= on_date]
    latest = {}
    for doc in eligible:
        key = doc.title.casefold()
        if key not in latest or doc.effective_date > latest[key].effective_date:
            latest[key] = doc
        elif (
            doc.effective_date == latest[key].effective_date
            and doc.document_id != latest[key].document_id
        ):
            raise ValueError("Ambiguous policy versions share a title and effective date.")
    scored = [
        (len(tokens & set(re.findall(r"[a-z]{3,}", c.text.lower()))), doc, c)
        for doc in latest.values()
        for c in doc.chunks
    ]
    scored.sort(key=lambda item: (-item[0], item[1].document_id, item[2].page, item[2].chunk_id))
    return [(doc, chunk) for score, doc, chunk in scored[:limit] if score > 0]


# Deliberately narrow, reviewable grammar. Other policy clauses are guidance, not auto-enforced.
LIMIT_RULE = re.compile(
    r"^(Travel|Software|Supplies) expenses must not exceed EUR "
    r"(\d+(?:\.\d{1,2})?) per transaction\.$",
    re.I,
)


def policy_evidence(
    data: ValidatedData, documents: tuple[PolicyDocument, ...]
) -> tuple[list[PolicyCitation], int | None]:
    """Evaluate only explicit supported per-transaction limits; retrieve other guidance separately."""
    citations = []
    evaluated = 0
    cache = {}
    seen = set()
    guidance_seen = set()
    for _, row in data.eligible.iterrows():
        day = row["date"].date()
        key = (row["category"].casefold(), day)
        if key not in cache:
            cache[key] = retrieve(documents, row["category"] + " expenses", day, limit=10000)
        for doc, chunk in cache[key]:
            matched = False
            for line in chunk.text.splitlines():
                match = LIMIT_RULE.fullmatch(line.strip())
                if not match or match.group(1).casefold() != row["category"].casefold():
                    continue
                threshold = cents(match.group(2))
                if threshold is None:
                    continue
                identity = (doc.document_id, line.strip(), int(row["source_row"]))
                if identity in seen:
                    continue
                seen.add(identity)
                matched = True
                evaluated += 1
                if int(row["amount_cents"]) > threshold:
                    citations.append(
                        PolicyCitation(
                            document_id=doc.document_id,
                            chunk_id=chunk.chunk_id,
                            title=doc.title,
                            version=doc.version,
                            effective_date=doc.effective_date,
                            page=chunk.page,
                            section=chunk.section,
                            quote=line.strip(),
                            source_row=int(row["source_row"]),
                            transaction_id=row["transaction_id"],
                            assessment="potential_violation",
                            explanation="Recorded amount exceeds the cited per-transaction category limit; "
                            "review applicability, exceptions and approval evidence.",
                            threshold_cents=threshold,
                            observed_cents=int(row["amount_cents"]),
                        )
                    )
            guidance_key = (doc.document_id, chunk.chunk_id, row["category"].casefold())
            if not matched and guidance_key not in guidance_seen and len(guidance_seen) < 12:
                guidance_seen.add(guidance_key)
                citations.append(
                    PolicyCitation(
                        document_id=doc.document_id,
                        chunk_id=chunk.chunk_id,
                        title=doc.title,
                        version=doc.version,
                        effective_date=doc.effective_date,
                        page=chunk.page,
                        section=chunk.section,
                        quote=chunk.text[:500],
                        source_row=int(row["source_row"]),
                        transaction_id=row["transaction_id"],
                        assessment="related_guidance",
                        observed_cents=int(row["amount_cents"]),
                        explanation="Retrieved passage for human review; no automatic violation conclusion.",
                    )
                )
    return citations, evaluated if evaluated else None


def verify_citation(
    citation: PolicyCitation, data: ValidatedData, documents: tuple[PolicyDocument, ...]
) -> None:
    """Reject invented pages, versions, quotes, transactions and unsupported violation claims."""
    doc = next((d for d in documents if d.document_id == citation.document_id), None)
    if doc is None or hashlib.sha256(doc.source).hexdigest() != doc.document_id:
        raise ValueError("Unverified policy document reference.")
    chunk = next((c for c in doc.chunks if c.chunk_id == citation.chunk_id), None)
    if chunk is None or (
        citation.title,
        citation.version,
        citation.effective_date,
        citation.page,
        citation.section,
    ) != (doc.title, doc.version, doc.effective_date, chunk.page, chunk.section):
        raise ValueError("Unverified policy page, version or section.")
    # Re-extract from retained bytes: metadata/chunks cannot be forged by an LLM or caller.
    original = extract_policy(doc.source, doc.title, doc.version, doc.effective_date)
    if chunk not in original.chunks or not citation.quote or citation.quote not in chunk.text:
        raise ValueError("Unverified policy quotation.")
    rows = data.eligible[data.eligible["source_row"].eq(citation.source_row)]
    if len(rows) != 1 or rows.iloc[0]["transaction_id"] != citation.transaction_id:
        raise ValueError("Policy citation references an invalid transaction.")
    row = rows.iloc[0]
    day = row["date"].date()
    if doc.effective_date > day or doc.document_id not in {
        d.document_id for d, _ in retrieve(documents, citation.quote, day, limit=1000)
    }:
        raise ValueError("Policy was not applicable on the transaction date.")
    if citation.observed_cents != int(row["amount_cents"]):
        raise ValueError("Policy observation does not match the transaction amount.")
    if citation.assessment == "related_guidance":
        if citation.threshold_cents is not None or citation.explanation != (
            "Retrieved passage for human review; no automatic violation conclusion."
        ):
            raise ValueError("Unsupported guidance conclusion.")
        return
    if citation.explanation != (
        "Recorded amount exceeds the cited per-transaction category limit; "
        "review applicability, exceptions and approval evidence."
    ):
        raise ValueError("Unsupported policy explanation.")
    match = LIMIT_RULE.fullmatch(citation.quote)
    if (
        citation.assessment != "potential_violation"
        or not match
        or match.group(1).casefold() != row["category"].casefold()
        or citation.threshold_cents != cents(match.group(2))
        or int(row["amount_cents"]) <= citation.threshold_cents
    ):
        raise ValueError("Unsupported policy violation claim.")
