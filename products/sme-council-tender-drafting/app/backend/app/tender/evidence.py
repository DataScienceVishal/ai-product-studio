"""Evidence numbering and retrieval (DESIGN 4.2). Every query carries tenant_id in SQL."""
from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


TOP_K, PER_DOC, CANDIDATES = 8, 3, 300
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


# Domain synonyms (DESIGN 4.2): bid wording for the same thing. Words are stemmed with the same 'english' config as the
# passages, so "mobilising" finds "mobilisation". Expansion terms count EXPANSION_WEIGHT of a question term. General
# tender vocabulary only; never a product, client or question name.
SYNONYMS: dict[str, str] = {
    "mobilisation": "transition handover implementation tupe onboarding", "tupe": "mobilisation transfer",
    "transition": "mobilisation", "complaint": "account management reporting escalation",
    "report": "account management", "kpi": "account management reporting",
    "supervision": "personnel roles management", "staffing": "personnel roles", "holiday": "cover absence personnel",
    "sickness": "cover absence", "quality": "policy audit inspection", "training": "induction qualification",
    "induction": "training", "continuity": "disaster recovery contingency",
    "carbon": "emissions vehicles sustainability", "environmental": "sustainability emissions",
    "safety": "risk policy", "social": "apprenticeship local community", "case": "client results challenge",
    "references": "client results challenge", "safeguarding": "children dbs", "monitor": "inspection audit",
    "recruit": "vetting induction",
}
EXPANSION_WEIGHT, BM25_K1, BM25_B = 0.3, 1.2, 0.75
_LEX = re.compile(r"'((?:[^']|'')+)'")
_TV = re.compile(r"'((?:[^']|'')+)':([0-9A-D,]+)")
_WORD = re.compile(r"[a-z]+")


def _lexemes(db: Session, s: str) -> list[str]:
    return [m.group(1).replace("''", "'") for m in _LEX.finditer(db.execute(text("SELECT to_tsvector('english', :s)::text"), {"s": s}).scalar_one())]


def _expansions(db: Session, question: str, base: set[str]) -> list[str]:
    keys = {}
    for k in SYNONYMS:
        for lex in _lexemes(db, k):
            keys.setdefault(lex, k)
    words = " ".join(w for w in dict.fromkeys(_WORD.findall(question.lower())))
    asked = {k for lex in _lexemes(db, words) if (k := keys.get(lex))}
    out: list[str] = []
    for k in asked:
        for lex in _lexemes(db, SYNONYMS[k]):
            if lex not in base and lex not in out:
                out.append(lex)
    return out


_STATS = text("""
SELECT count(*) AS n, coalesce(avg(length(e.tsv)), 0) AS avg_len
FROM evidence_items e JOIN source_documents d ON d.tenant_id = e.tenant_id AND d.id = e.document_id
WHERE e.tenant_id = :tenant AND e.deleted_at IS NULL AND d.tenant_id = :tenant AND d.kind = 'evidence' AND d.deleted_at IS NULL
""")
_DF = text("""
SELECT l.lex, count(e.id) AS df
FROM unnest(CAST(:lexes AS text[])) AS l(lex)
LEFT JOIN (evidence_items e JOIN source_documents d ON d.tenant_id = e.tenant_id AND d.id = e.document_id
           AND d.kind = 'evidence' AND d.deleted_at IS NULL)
  ON e.tenant_id = :tenant AND e.deleted_at IS NULL AND e.tsv @@ quote_literal(l.lex)::tsquery
GROUP BY l.lex
""")
_CAND = text("""
SELECT e.id, e.display_no, e.document_id, d.filename, e.page_from, e.page_to, e.heading, e.text, e.tsv::text AS tv
FROM evidence_items e
JOIN source_documents d ON d.tenant_id = e.tenant_id AND d.id = e.document_id
WHERE e.tenant_id = :tenant AND e.deleted_at IS NULL AND d.tenant_id = :tenant AND d.kind = 'evidence' AND d.deleted_at IS NULL
  AND e.tsv @@ (SELECT string_agg(quote_literal(x), ' | ')::tsquery FROM unnest(CAST(:lexes AS text[])) AS u(x))
ORDER BY ts_rank_cd(e.tsv, (SELECT string_agg(quote_literal(x), ' | ')::tsquery FROM unnest(CAST(:lexes AS text[])) AS u(x)), 32) DESC, e.display_no
LIMIT :cands
""")


def _bm25(tv: str, weights: dict[str, float], idf: dict[str, float], avg_len: float) -> float:
    tf = {m.group(1).replace("''", "'"): m.group(2).count(",") + 1 for m in _TV.finditer(tv)}
    length = sum(tf.values()) or 1
    norm = BM25_K1 * (1 - BM25_B + BM25_B * length / (avg_len or length))
    return sum(w * idf[t] * tf[t] * (BM25_K1 + 1) / (tf[t] + norm) for t, w in weights.items() if t in tf)


def search_evidence(db: Session, tenant_id: uuid.UUID, question: str, *, limit: int = TOP_K,
                    per_doc: int = PER_DOC, min_score: float = 0.0) -> list[Hit]:
    """Top `limit` passages for the question: OR full-text candidates (question words plus domain synonyms), rescored by
    BM25 so rare words count more than "describe" and "arrangements", then the must-have token boost and a per-document cap.
    `rank` is the BM25 score as a fraction of the best candidate's (0 to 1), so a code boost of 1.0 still beats any rank."""
    question = (question or "")[:2000]
    own = list(dict.fromkeys(_lexemes(db, question) if question.strip() else []))
    own = [t for t in own if db.execute(text("SELECT numnode(plainto_tsquery('english', :t))"), {"t": t}).scalar_one() > 0]
    if not own:
        return []
    weights = {t: 1.0 for t in own} | {t: EXPANSION_WEIGHT for t in _expansions(db, question, set(own))}
    lexes = list(weights)
    st = db.execute(_STATS, {"tenant": tenant_id}).one()
    n = int(st.n)
    df = {r.lex: int(r.df) for r in db.execute(_DF, {"lexes": lexes, "tenant": tenant_id})}
    idf = {t: math.log(1 + (n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5)) for t in lexes}
    rows = db.execute(_CAND, {"lexes": lexes, "tenant": tenant_id, "cands": CANDIDATES}).all()
    scored = [(_bm25(r.tv, weights, idf, float(st.avg_len)), r) for r in rows]
    top = max((s for s, _ in scored), default=0.0) or 1.0
    tokens = must_have_tokens(question)
    hits = []
    for raw, r in scored:
        if raw <= 0:
            continue
        boost = min(MAX_BOOST, sum(w for pat, w in tokens if pat.search(r.heading + " " + r.text)))
        rank = raw / top
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
