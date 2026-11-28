"""Evidence numbering and retrieval (DESIGN 4.2). Every query carries tenant_id in SQL."""
from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


TOP_K, PER_DOC, CANDIDATES = 8, 3, 300
CODE_BOOST, MAX_BOOST = 1.0, 3.0  # rank is BM25 over its own ceiling, so always below 1: a code match (+1.0) always wins
TOKEN_BOOST = 0.25  # year/acronym weight is a FRACTION of the search's best rank (one value chosen a priori, not tuned on labels)
# Pseudo-relevance feedback (RM3 style, T-216 slice 4). Parameters are the Anserini / Lavrenko & Croft defaults, fixed a priori
# (DESIGN 4.2), never tuned on the demo labels. PRF_ENABLED=False gives the old ranking exactly.
PRF_ENABLED, PRF_FB_DOCS, PRF_FB_TERMS, PRF_ORIG_WEIGHT = True, 10, 10, 0.5
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


def must_have_tokens(question: str) -> list[tuple[re.Pattern, float, str]]:
    """(pattern, weight, kind) per token; kind is "code" (absolute boost) or "relative" (year/acronym, a fraction of the best rank)."""
    found: dict[str, tuple[float, str]] = {}
    for m in _CODES.finditer(question):
        found[re.sub(r"\s+", " ", m.group(0).strip()).lower()] = (CODE_BOOST, "code")
    for m in _YEAR.finditer(question):
        found.setdefault(m.group(0), (TOKEN_BOOST, "relative"))
    for m in _ACRONYM.finditer(question):
        if m.group(0) not in _ACRONYM_SKIP:
            found.setdefault(m.group(0).lower(), (TOKEN_BOOST, "relative"))
    out = []
    for tok, (weight, kind) in found.items():
        tok = re.sub(r"^iso\s?(?=\d)", "iso ", tok)  # ISO14001 and ISO 14001 are the same token
        pattern = r"\s*".join(re.escape(part) for part in re.split(r"\s+", tok))
        out.append((re.compile(rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])", re.I), weight, kind))
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


# BM25 over the full-text candidates (DESIGN 4.2). Terms are the question's own lexemes (to_tsvector('english'), so stopwords
# are already gone and words are stemmed like the passages). df, document count and average length come from the tenant's
# own passages. Length is the number of distinct lexemes in the passage on both sides (document length and the average).
BM25_K1, BM25_B = 1.2, 0.75
_LEX = re.compile(r"'((?:[^']|'')+)'")
_TV = re.compile(r"'((?:[^']|'')+)':([0-9A-D,]+)")


def _lexemes(db: Session, s: str) -> list[str]:
    return [m.group(1).replace("''", "'") for m in _LEX.finditer(db.execute(text("SELECT to_tsvector('english', :s)::text"), {"s": s}).scalar_one())]


_STATS = text("""
SELECT count(*) AS n, coalesce(avg(length(e.tsv)), 0) AS avg_len
FROM evidence_items e JOIN source_documents d ON d.tenant_id = e.tenant_id AND d.id = e.document_id
WHERE e.tenant_id = :tenant AND e.deleted_at IS NULL AND d.tenant_id = :tenant AND d.kind = 'evidence' AND d.deleted_at IS NULL
""")
_DF = text("""
SELECT l.lex, count(e.id) AS df
FROM unnest(CAST(:lexes AS text[])) AS l(lex)
LEFT JOIN (evidence_items e JOIN source_documents d ON d.tenant_id = e.tenant_id AND d.id = e.document_id
           AND d.tenant_id = :tenant AND d.kind = 'evidence' AND d.deleted_at IS NULL)
  ON e.tenant_id = :tenant AND e.deleted_at IS NULL AND e.tsv @@ quote_literal(l.lex)::tsquery
GROUP BY l.lex
""")
_CAND = text("""
SELECT e.id, e.display_no, e.document_id, d.filename, e.page_from, e.page_to, e.heading, e.text, e.tsv::text AS tv
FROM evidence_items e
JOIN source_documents d ON d.tenant_id = e.tenant_id AND d.id = e.document_id
WHERE e.tenant_id = :tenant AND e.deleted_at IS NULL AND d.tenant_id = :tenant AND d.kind = 'evidence' AND d.deleted_at IS NULL
  AND e.tsv @@ (SELECT string_agg(quote_literal(x), ' | ')::tsquery FROM unnest(CAST(:own AS text[])) AS u(x))
ORDER BY ts_rank_cd(e.tsv, (SELECT string_agg(quote_literal(x), ' | ')::tsquery FROM unnest(CAST(:own AS text[])) AS u(x)), 32) DESC, e.display_no
LIMIT :cands
""")


def _bm25(tv: str, idf: dict[str, float], avg_len: float) -> float:
    """BM25 of one passage (its tsvector text) for the question terms in `idf`. Length and `avg_len` are both counts of
    distinct lexemes (what `length(tsvector)` gives in SQL)."""
    tf = {m.group(1).replace("''", "'"): m.group(2).count(",") + 1 for m in _TV.finditer(tv)}
    length = len(tf) or 1
    norm = BM25_K1 * (1 - BM25_B + BM25_B * length / (avg_len or length))
    return sum(idf[t] * tf[t] * (BM25_K1 + 1) / (tf[t] + norm) for t in idf if t in tf)


def _prf_weights(first: list[tuple[str, float]], own: list[str], idf: dict[str, float], df_of, avg_len: float) -> tuple[dict[str, float], dict[str, float]]:
    """RM3 query model. `first` = [(tsvector text, first-pass rank)] best first. Doc weight = rank / sum of ranks of the top
    PRF_FB_DOCS; term weight = sum over those docs of doc weight x (tf / distinct-lexeme length) x idf; keep the PRF_FB_TERMS
    highest, normalise to 1 and scale by (1 - PRF_ORIG_WEIGHT); the original terms share PRF_ORIG_WEIGHT equally. Returns
    ({lexeme: weight} summing to 1, idf of every term in it). Ties break on the lexeme, so it is deterministic."""
    top = first[:PRF_FB_DOCS]
    total = sum(r for _, r in top)
    if not top or total <= 0:
        return {}, idf
    acc: dict[str, float] = {}
    tfs = []
    for tv, r in top:
        tf = {m.group(1).replace("''", "'"): m.group(2).count(",") + 1 for m in _TV.finditer(tv)}
        tfs.append((tf, r / total))
        for t in tf:
            acc.setdefault(t, 0.0)
    idf_all = dict(idf)
    idf_all.update(df_of([t for t in acc if t not in idf_all]))
    for tf, dw in tfs:
        ln = len(tf) or 1
        for t, c in tf.items():
            acc[t] += dw * (c / ln) * idf_all[t]
    best = sorted(acc.items(), key=lambda kv: (-kv[1], kv[0]))[:PRF_FB_TERMS]
    z = sum(w for _, w in best)
    if z <= 0:
        return {}, idf
    q = {t: PRF_ORIG_WEIGHT / len(own) for t in own}
    for t, w in best:
        q[t] = q.get(t, 0.0) + (1 - PRF_ORIG_WEIGHT) * w / z
    return q, idf_all


def search_evidence(db: Session, tenant_id: uuid.UUID, question: str, *, limit: int = TOP_K,
                    per_doc: int = PER_DOC, min_score: float = 0.0) -> list[Hit]:
    """Top `limit` passages for the question: OR full-text candidates (a passage must hold a word of the question), rescored by
    BM25 so rare words count more than "describe" and "arrangements", then the must-have token boost and a per-document cap.
    `rank` is absolute: the BM25 score as a fraction of the most the question's terms could score (idf times k1+1, summed),
    so it is in (0, 1) and a weak match stays low. A code boost of 1.0 therefore always beats any rank. Year and acronym
    tokens together add at most TOKEN_BOOST x the best candidate's rank (min(number of matching year/acronym tokens, 1) x TOKEN_BOOST x best),
    so they reorder close candidates only. `min_score` (RETRIEVAL_FLOOR) tests `rank`, never the boosted score, so a relative
    boost cannot lift a weak search over the floor; a passage holding an asked-for code passes it regardless. Sorting is by
    score. Four statements per search."""
    question = (question or "")[:2000]
    own = list(dict.fromkeys(_lexemes(db, question) if question.strip() else []))
    if not own:
        return []
    st = db.execute(_STATS, {"tenant": tenant_id}).one()
    n = int(st.n)
    df = {r.lex: int(r.df) for r in db.execute(_DF, {"lexes": own, "tenant": tenant_id})}
    idf = {t: math.log(1 + (n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5)) for t in own}
    ceiling = sum(idf.values()) * (BM25_K1 + 1) or 1.0
    rows = db.execute(_CAND, {"own": own, "tenant": tenant_id, "cands": CANDIDATES}).all()
    tokens = must_have_tokens(question)
    scored = [(r, raw / ceiling) for r in rows if (raw := _bm25(r.tv, idf, float(st.avg_len))) > 0]
    # second pass (PRF): same candidates rescored with the RM3 query model; `rank` (and so the floor) stays the first-pass value
    rank2 = {r.id: rank for r, rank in scored}
    if PRF_ENABLED and scored:
        def df_of(lexes):
            if not lexes:
                return {}
            d = {x.lex: int(x.df) for x in db.execute(_DF, {"lexes": lexes, "tenant": tenant_id})}
            return {t: math.log(1 + (n - d.get(t, 0) + 0.5) / (d.get(t, 0) + 0.5)) for t in lexes}
        ordered = sorted(scored, key=lambda x: (-x[1], x[0].display_no))
        q, idf2 = _prf_weights([(r.tv, rk) for r, rk in ordered], own, idf, df_of, float(st.avg_len))
        if q:
            wi = {t: w * idf2[t] for t, w in q.items()}
            c2 = sum(wi.values()) * (BM25_K1 + 1) or 1.0
            rank2 = {r.id: _bm25(r.tv, wi, float(st.avg_len)) / c2 for r, _ in scored}
    best = max(rank2.values(), default=0.0)
    hits, coded = [], set()
    for r, rank in scored:
        hay = r.heading + " " + r.text
        code = sum(w for pat, w, kind in tokens if kind == "code" and pat.search(hay))
        rel = sum(w for pat, w, kind in tokens if kind == "relative" and pat.search(hay))
        # code: absolute (+1.0 beats any rank); year/acronym: relative, summed part capped at one token's worth
        boost = min(MAX_BOOST, code + min(rel / TOKEN_BOOST, 1.0) * TOKEN_BOOST * best)
        if code:
            coded.add(r.id)
        hits.append(Hit(r.id, r.display_no, r.document_id, r.filename, r.page_from, r.page_to, r.heading, r.text,
                        rank, rank2[r.id] + boost))
    hits.sort(key=lambda h: (-h.score, h.display_no))
    out, per = [], {}
    for h in hits:
        if (h.rank < min_score and h.id not in coded) or per.get(h.document_id, 0) >= per_doc:
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
