"""Deterministic scorers for the acceptance bars A1 to A4, A6a, A7 and A8 (SPEC section 6, DESIGN 8.1). Stdlib only.

Ground truth (`eval/keys/`) is read only here and by the caller that loads it; the fake provider never sees it.

Key item   : {"ref", "kind": "question|mandatory|deadline", "text", "word_limit", "page_limit", "marks", "weight_pct"}
Extracted  : the app's ExtractItem dicts (same fields plus "pass_fail"); a key "mandatory" item is found only if matched
             to an extracted item that is kind "mandatory" or has pass_fail true, else it is `shown_optional`.
Matching   : by `ref` first (normalised), then by text similarity >= 0.8, one-to-one greedy (best pair first).
"""
from __future__ import annotations

import difflib
import re
from collections import defaultdict

SIM_THRESHOLD = 0.8
BARS = {"A1_recall": 0.90, "A1_precision": 0.90, "A2": 0.90, "A3": 0.85, "A4": 0.95, "A6a": 0.95, "A7": 1.0, "A8": 0.90}
LIMIT_FIELDS = ("word_limit", "page_limit", "marks", "weight_pct")
_CITE = re.compile(r"\[E-(\d+)\]")
_GAP = re.compile(r"\[NEEDS FIRM INPUT:[^\]]*\]")


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def match_items(key: list[dict], got: list[dict], threshold: float = SIM_THRESHOLD) -> list[tuple[int, int]]:
    """One-to-one pairs (key index, got index): equal refs first, then the highest text similarity >= threshold."""
    pairs, used_k, used_g = [], set(), set()
    for i, k in enumerate(key):
        ref = _norm(k.get("ref"))
        if not ref:
            continue
        for j, g in enumerate(got):
            if j not in used_g and _norm(g.get("ref")) == ref:
                pairs.append((i, j)); used_k.add(i); used_g.add(j)
                break
    cands = sorted(((similarity(k.get("text", ""), g.get("text", "")), i, j)
                    for i, k in enumerate(key) if i not in used_k
                    for j, g in enumerate(got) if j not in used_g), key=lambda t: (-t[0], t[1], t[2]))
    for score, i, j in cands:
        if score >= threshold and i not in used_k and j not in used_g:
            pairs.append((i, j)); used_k.add(i); used_g.add(j)
    return sorted(pairs)


def _ratio(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def _is_mandatory(item: dict) -> bool:
    return item.get("kind") == "mandatory" or bool(item.get("pass_fail"))


def score_extraction(packs: list[dict]) -> dict:
    """packs: [{"pack", "key": [items], "got": [items]}]. Pooled A1 (questions), A2 (stated limits and marks on matched
    question and mandatory items) and A3 (mandatory items), plus per-pack figures and every miss."""
    q_key = q_got = q_hit = 0
    stated = correct = 0
    m_key = m_found = 0
    shown_optional, per_pack, wrong_fields, missed_q = [], [], [], []
    for p in packs:
        key, got = p["key"], p["got"]
        kq = [k for k in key if k.get("kind") == "question"]
        gq = [g for g in got if g.get("kind") == "question"]
        pairs_q = match_items(kq, gq)
        q_key += len(kq); q_got += len(gq); q_hit += len(pairs_q)
        hit_k = {i for i, _ in pairs_q}
        missed_q += [{"pack": p["pack"], "ref": k.get("ref"), "text": k.get("text")} for i, k in enumerate(kq) if i not in hit_k]
        # A2 over matched question items, and mandatory items matched among all extracted items
        km = [k for k in key if k.get("kind") == "mandatory"]
        pairs_m = match_items(km, got)
        m_key += len(km)
        for i, j in pairs_m:
            if _is_mandatory(got[j]):
                m_found += 1
            else:
                shown_optional.append({"pack": p["pack"], "ref": km[i].get("ref")})
        for ks, gs, pairs in ((kq, gq, pairs_q), (km, got, pairs_m)):
            for i, j in pairs:
                for f in LIMIT_FIELDS:
                    if ks[i].get(f) is not None:
                        stated += 1
                        if gs[j].get(f) == ks[i].get(f):
                            correct += 1
                        else:
                            wrong_fields.append({"pack": p["pack"], "ref": ks[i].get("ref"), "field": f,
                                                 "key": ks[i].get(f), "got": gs[j].get(f)})
        per_pack.append({"pack": p["pack"], "questions_key": len(kq), "questions_found": len(pairs_q),
                         "questions_extracted": len(gq)})
    recall, precision = _ratio(q_hit, q_key), _ratio(q_hit, q_got)
    a2, a3 = _ratio(correct, stated), _ratio(m_found, m_key)
    return {
        "A1": {"recall": recall, "precision": precision, "key": q_key, "extracted": q_got, "matched": q_hit,
               "pass": recall is not None and precision is not None and recall >= BARS["A1_recall"] and precision >= BARS["A1_precision"],
               "missed": missed_q},
        "A2": {"score": a2, "stated": stated, "correct": correct, "pass": a2 is not None and a2 >= BARS["A2"], "wrong": wrong_fields},
        "A3": {"score": a3, "key": m_key, "found": m_found, "shown_optional": shown_optional,
               "pass": a3 is not None and a3 >= BARS["A3"] and not shown_optional},
        "per_pack": per_pack,
    }


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if s.strip()]


def count_words(text: str) -> int:
    """The pre-registered word-count rule (DESIGN 4.5): [E-n] markers excluded, gap markers included."""
    return len(_CITE.sub(" ", text).split())


def claims_of(text: str) -> list[str]:
    """Claims for A4: every sentence except a bare gap marker."""
    return [s for s in split_sentences(text) if _norm(_GAP.sub("", s)) and not (_GAP.fullmatch(s.strip()))]


def score_traceability(drafts: list[dict]) -> dict:
    """A4. drafts: [{"id", "text", "retrieved_ids", "live_ids"}]. A claim passes if it carries at least one [E-n] and every
    [E-n] in it is both a live passage of the tenant and in that draft's retrieved set."""
    total = ok = 0
    failures = []
    for d in drafts:
        live, retrieved = set(d.get("live_ids", [])), set(d.get("retrieved_ids", []))
        for claim in claims_of(d["text"]):
            total += 1
            ids = [int(n) for n in _CITE.findall(claim)]
            if ids and all(n in live and n in retrieved for n in ids):
                ok += 1
            else:
                failures.append({"draft": d["id"], "claim": claim, "reason": "no citation" if not ids else "does not resolve"})
    s = _ratio(ok, total)
    return {"score": s, "claims": total, "resolved": ok, "pass": s is not None and s >= BARS["A4"], "failures": failures}


def score_word_limits(drafts: list[dict]) -> dict:
    """A7. drafts: [{"id", "text", "word_limit"}]. Drafts with no stated limit are not scored. 100% required."""
    scored = [d for d in drafts if d.get("word_limit")]
    over = [{"draft": d["id"], "words": count_words(d["text"]), "limit": d["word_limit"]}
            for d in scored if count_words(d["text"]) > d["word_limit"]]
    s = _ratio(len(scored) - len(over), len(scored))
    return {"score": s, "scored": len(scored), "over": over, "pass": s is not None and s >= BARS["A7"]}


def score_gaps(answers: list[dict]) -> dict:
    """A8 (script half). answers: [{"id", "text"}] for the trap questions. A gap marker must be present."""
    with_gap = [a for a in answers if _GAP.search(a["text"])]
    s = _ratio(len(with_gap), len(answers))
    return {"score": s, "trap_questions": len(answers), "with_gap": len(with_gap),
            "missing": [a["id"] for a in answers if not _GAP.search(a["text"])],
            "pass": s is not None and s >= BARS["A8"], "note": "human check list still required"}


def _overlaps(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    return bool(na) and bool(nb) and (na in nb or nb in na)


def score_seeded_claims(seeded: list[dict], checked: list[dict]) -> dict:
    """A6a. seeded: [{"id", "draft", "type", "span"}]; checked: [{"draft", "span", "verdict"}] from the claim check run on
    the fixture drafts. A seeded claim is caught when a checker claim on the same draft overlaps its span (normalised
    substring either way) with verdict unsupported or contradicted. `unchecked` and `supported` are misses."""
    by_draft = defaultdict(list)
    for c in checked:
        by_draft[c["draft"]].append(c)
    caught, misses, per_type = 0, [], defaultdict(lambda: [0, 0])
    for s in seeded:
        hit = any(c["verdict"] in ("unsupported", "contradicted") and _overlaps(c["span"], s["span"])
                  for c in by_draft.get(s["draft"], []))
        per_type[s["type"]][1] += 1
        if hit:
            caught += 1; per_type[s["type"]][0] += 1
        else:
            misses.append({"id": s["id"], "type": s["type"], "draft": s["draft"], "span": s["span"]})
    total = len(seeded)
    return {"caught": caught, "total": total, "score": _ratio(caught, total),
            "pass": total > 0 and caught / total >= BARS["A6a"],
            "per_type": {t: {"caught": c, "total": n} for t, (c, n) in sorted(per_type.items())}, "misses": misses}
