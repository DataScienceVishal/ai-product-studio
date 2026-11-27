"""Evidence numbering and retrieval (DESIGN 4.2). Every query carries tenant_id in SQL."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


TOP_K, PER_DOC, CANDIDATES = 8, 3, 100
CODE_BOOST, TOKEN_BOOST, MAX_BOOST = 1.0, 0.25, 3.0  # ts_rank_cd(..., 32) is below 1, so a code match always wins
_CODES = re.compile(r"(?i)\bISO\s?\d{4,5}(?:[-:]\d{1,4})?|\bCHAS\b|\bSafe\s?Contractor\b|\bConstructionline\b|\bCyber\s+Essentials(?:\s+Plus)?\b")
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_ACRONYM = re.compile(r"\b[A-Z]{3,6}\b")
_ACRONYM_SKIP = {"THE", "AND", "FOR", "WITH", "ALL", "ANY", "NOT", "ARE", "YOU", "OUR", "HOW", "WHAT", "WHO", "ISO"}


def allocate_numbers(db: Session, tenant_id: uuid.UUID, count: int) -> int:
    """Reserve `count` E-numbers for the tenant and return the first. The counter only goes up, so a number is never
    reused; it lives in the caller's transaction, so a failed upload gives its numbers back. The advisory lock
    serialises concurrent uploads of one tenant."""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": f"evidence:{tenant_id}"})
    return db.execute(text(
        "INSERT INTO evidence_counters (tenant_id, next_no) VALUES (:t, 1 + :n) "
        "ON CONFLICT (tenant_id) DO UPDATE SET next_no = evidence_counters.next_no + :n "
        "RETURNING next_no - :n"), {"t": tenant_id, "n": count}).scalar_one()


def must_have_tokens(question: str) -> list[tuple[re.Pattern, float]]:
    found: dict[str, float] = {}
    for m in _CODES.finditer(question):
        found[re.sub(r"\s+", " ", m.group(0).strip()).lower()] = CODE_BOOST
    for m in _YEAR.finditer(question):
        found.setdefault(m.group(0), TOKEN_BOOST)
    for m in _ACRONYM.finditer(question):
        if m.group(0) not in _ACRONYM_SKIP:
            found.setdefault(m.group(0).lower(), TOKEN_BOOST)
    out = []
    for tok, weight in found.items():
        tok = re.sub(r"^iso\s?(?=\d)", "iso ", tok)  # ISO14001 and ISO 14001 are the same token
        pattern = r"\s*".join(re.escape(part) for part in re.split(r"\s+", tok))
        out.append((re.compile(rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])", re.I), weight))
    return out


@dataclass
class Hit:
    id: uuid.UUID
    display_no: int
    document_id: uuid.UUID
    document_name: str
    page_from: int
    page_to: int
    heading: str
    text: str
    rank: float
    score: float


_SQL = text("""
WITH q AS (
  SELECT CASE WHEN numnode(pq) = 0 THEN NULL ELSE replace(pq::text, '&', '|')::tsquery END AS tq
  FROM (SELECT plainto_tsquery('english', :q) AS pq) s
)
SELECT e.id, e.display_no, e.document_id, d.filename, e.page_from, e.page_to, e.heading, e.text,
       ts_rank_cd(e.tsv, q.tq, 32) AS rank
FROM evidence_items e
JOIN source_documents d ON d.tenant_id = e.tenant_id AND d.id = e.document_id
CROSS JOIN q
WHERE e.tenant_id = :tenant AND e.deleted_at IS NULL AND d.tenant_id = :tenant AND d.kind = 'evidence'
  AND q.tq IS NOT NULL AND e.tsv @@ q.tq
ORDER BY rank DESC, e.display_no
LIMIT :cands
""")


def search_evidence(db: Session, tenant_id: uuid.UUID, question: str, *, limit: int = TOP_K,
                    per_doc: int = PER_DOC, min_score: float = 0.0) -> list[Hit]:
    """Top `limit` passages for the question: OR full-text query, must-have token boost, at most `per_doc` per document."""
    question = (question or "")[:2000]
    rows = db.execute(_SQL, {"q": question, "tenant": tenant_id, "cands": CANDIDATES}).all()
    tokens = must_have_tokens(question)
    hits = []
    for r in rows:
        boost = min(MAX_BOOST, sum(w for pat, w in tokens if pat.search(r.heading + " " + r.text)))
        rank = float(r.rank)
        hits.append(Hit(r.id, r.display_no, r.document_id, r.filename, r.page_from, r.page_to, r.heading, r.text,
                        rank, rank + boost))
    hits.sort(key=lambda h: (-h.score, h.display_no))
    out, per = [], {}
    for h in hits:
        if h.score < min_score or per.get(h.document_id, 0) >= per_doc:
            continue
        per[h.document_id] = per.get(h.document_id, 0) + 1
        out.append(h)
        if len(out) == limit:
            break
    return out


def next_numbers(db: Session, tenant_id: uuid.UUID, n: int) -> list[int]:
    if n == 0:
        return []
    start = allocate_numbers(db, tenant_id, n)
    return list(range(start, start + n))
