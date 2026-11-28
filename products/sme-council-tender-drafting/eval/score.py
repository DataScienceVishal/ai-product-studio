"""Deterministic scorers for the acceptance bars A1 to A4, A6a, A7 and A8 (SPEC section 6, DESIGN 8.1). Stdlib only.

Ground truth (`eval/keys/`) is read only here and by the caller that loads it; the fake provider never sees it.

Key item   : {"ref", "kind": "question|mandatory|deadline", "text", "word_limit", "page_limit", "marks", "weight_pct"}
Extracted  : the app's ExtractItem dicts (same fields plus "pass_fail"); a key "mandatory" item is found only if matched
             to an extracted item that is kind "mandatory" or has pass_fail true, else it is `shown_optional`.
Matching   : by `ref` first (normalised), then by text similarity >= 0.8, one-to-one greedy (best pair first).

Sentence splitting and word counting are the app's own (`app.tender.draft.split_sentences`, `count_words`), imported so the
scorer cannot drift from what the product enforces. Everything else is stdlib.

A2 (stated fields): for every matched question and mandatory item, each non-null key value of `word_limit`, `page_limit`,
`marks` and `weight_pct` is a stated field and must equal the extracted value. Invented limits (T-213): a null key
`word_limit` or `page_limit` means "this item has no limit of its own" (key rules 7-9), so a non-null extracted value there is
a stated field that is wrong (it also adds `"invented": True` to its `wrong` row). A non-null extracted `marks` or
`weight_pct` against a null key is not scored (the key leaves them null when the pack is not unambiguous) and is only listed
under `invented_unscored`. Null against null is ignored.

Deadline (T-213): report-only, never in BARS and never part of `pass`. `result["deadline"]` holds, per pack with a key deadline,
whether an extracted deadline item (kind "deadline" or a non-empty `deadline` field) carries the key's day, month and year
(`found`, from `score_deadline`), and separately whether the time matches; pooled `found` and `total`.
"""
from __future__ import annotations

import difflib
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "backend"))
from app.tender.draft import _CITE, _GAP, count_words, split_sentences  # noqa: E402,F401

SIM_THRESHOLD = 0.8
REF_SIM_MIN = 0.5      # an equal ref also needs this much text similarity, so a wrong item with a reused number is not a match
BARS = {"A1_recall": 0.90, "A1_precision": 0.90, "A2": 0.90, "A3": 0.85, "A4": 0.95, "A6a": 0.95, "A7": 1.0, "A8": 0.90}
LIMIT_FIELDS = ("word_limit", "page_limit", "marks", "weight_pct")
INVENTED_SCORED_FIELDS = ("word_limit", "page_limit")   # key null + extracted non-null counts as wrong; marks and weight are only listed


def _norm(s) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def match_items(key: list[dict], got: list[dict], threshold: float = SIM_THRESHOLD, ref_ok=None) -> list[tuple[int, int]]:
    """One-to-one pairs (key index, got index): equal refs first (only with extracted items `ref_ok` accepts, default all),
    then the highest text similarity >= threshold. A ref match also needs similarity >= REF_SIM_MIN."""
    pairs, used_k, used_g = [], set(), set()
    for i, k in enumerate(key):
        ref = _norm(k.get("ref"))
        if not ref:
            continue
        for j, g in enumerate(got):
            if j not in used_g and _norm(g.get("ref")) == ref and (ref_ok is None or ref_ok(g)) \
                    and similarity(k.get("text", ""), g.get("text", "")) >= REF_SIM_MIN:
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


_MONTHS = {m: i for i, m in enumerate(
    "january february march april may june july august september october november december".split(), 1)}
_MONTHS.update({"sept": 9, **{m[:3]: i for m, i in list(_MONTHS.items())}})
_MON = "|".join(sorted(_MONTHS, key=len, reverse=True))
_D_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})(?!\d)")
_D_NUM = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b")
_D_DMY = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MON})\b\.?,?\s+(\d{{4}})\b", re.I)
_D_MDY = re.compile(rf"\b({_MON})\b\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I)
_T_HM = re.compile(r"(?<![\d.:])(\d{1,2})[:.](\d{2})(?!\d|\.\d)(?!\s*[ap]\.?m\b)", re.I)   # "30.04.2027" is a date, not a time
_T_AMPM = re.compile(r"(?<![\d:.])(\d{1,2})(?:[:.](\d{2}))?\s*([ap])\.?m\b", re.I)
_T_NOON = re.compile(r"\b(?:noon|midday)\b", re.I)


def parse_deadline_text(s) -> dict:
    """Dates and times named in free text: {"dates": {(y, m, d)}, "times": {(h, min)}}. Handles "Friday 30 April 2027",
    "30th of April 2027", "April 30, 2027", 2027-04-30T12:00, 30/04/2027 (day first), "12:00", "2pm", "12 noon", "midday"."""
    s = str(s or "")
    dates = set()
    for y, mo, d in _D_ISO.findall(s):
        dates.add((int(y), int(mo), int(d)))
    for d, mo, y in _D_NUM.findall(s):
        dates.add((int(y), int(mo), int(d)))
    for d, mo, y in _D_DMY.findall(s):
        dates.add((int(y), _MONTHS[mo.lower()], int(d)))
    for mo, d, y in _D_MDY.findall(s):
        dates.add((int(y), _MONTHS[mo.lower()], int(d)))
    times = {(int(h), int(mi)) for h, mi in _T_HM.findall(s) if int(h) < 24 and int(mi) < 60}
    for h, mi, ap in _T_AMPM.findall(s):
        times.add(((int(h) % 12) + (12 if ap.lower() == "p" else 0), int(mi or 0)))
    if _T_NOON.search(s):
        times.add((12, 0))
    return {"dates": dates, "times": times}


def score_deadline(packs: list[dict]) -> dict:
    """Report-only deadline check (never a bar). Per pack that has a key deadline: `found` when one extracted deadline item
    holds the key's full date, `time_match` when one holds the key's time (None if the key has no time or the date was not found)."""
    rows, found = [], 0
    for p in packs:
        kd = next((k for k in p["key"] if k.get("kind") == "deadline"), None)
        if kd is None:
            continue
        want = parse_deadline_text(kd.get("text"))
        cands = [g for g in p["got"] if g.get("kind") == "deadline" or str(g.get("deadline") or "").strip()]
        texts = [f"{g.get('text') or ''} {g.get('deadline') or ''}".strip() for g in cands]
        hit = time_hit = False
        for t in texts:
            have = parse_deadline_text(t)
            if want["dates"] and want["dates"] <= have["dates"]:
                hit = True
                if want["times"] and want["times"] <= have["times"]:
                    time_hit = True
        rows.append({"pack": p["pack"], "key_text": kd.get("text"), "found": hit, "got": texts,
                     "time_match": (time_hit if want["times"] else None) if hit else None})
        found += hit
    return {"packs": rows, "found": found, "total": len(rows)}


def score_extraction(packs: list[dict]) -> dict:
    """packs: [{"pack", "key": [items], "got": [items]}]. Pooled A1 (questions), A2 (stated limits and marks on matched
    question and mandatory items) and A3 (mandatory items), plus per-pack figures and every miss."""
    q_key = q_got = q_hit = 0
    stated = correct = 0
    m_key = m_found = 0
    shown_optional, per_pack, wrong_fields, missed_q, invented_unscored = [], [], [], [], []
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
        # refs are matched only against non-question items: a question that shares a ref with a mandatory item must not pair up
        pairs_m = match_items(km, got, ref_ok=lambda g: g.get("kind") != "question")
        m_key += len(km)
        for i, j in pairs_m:
            if _is_mandatory(got[j]):
                m_found += 1
            else:
                shown_optional.append({"pack": p["pack"], "ref": km[i].get("ref")})
        for ks, gs, pairs in ((kq, gq, pairs_q), (km, got, pairs_m)):
            for i, j in pairs:
                for f in LIMIT_FIELDS:
                    if ks[i].get(f) is None and gs[j].get(f) is not None:
                        if f in INVENTED_SCORED_FIELDS:   # a null key limit means "no limit of its own": an invented one is wrong
                            stated += 1
                            wrong_fields.append({"pack": p["pack"], "ref": ks[i].get("ref"), "field": f,
                                                 "key": None, "got": gs[j].get(f), "invented": True})
                        else:
                            invented_unscored.append({"pack": p["pack"], "ref": ks[i].get("ref"), "field": f, "got": gs[j].get(f)})
                    elif ks[i].get(f) is not None:
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
        "A2": {"score": a2, "stated": stated, "correct": correct, "pass": a2 is not None and a2 >= BARS["A2"], "wrong": wrong_fields,
               "invented_unscored": invented_unscored},
        "A3": {"score": a3, "key": m_key, "found": m_found, "shown_optional": shown_optional,
               "pass": a3 is not None and a3 >= BARS["A3"] and not shown_optional},
        "deadline": score_deadline(packs),
        "per_pack": per_pack,
    }


# Words that carry no factual content once the gap marker is stripped from a gap sentence.
CONNECTIVES = frozenset("a an and are as at be but by for from has have had if in is it its of on or our so that the their "
                        "then there these this those to we was were which while will with would you your also".split())


RESIDUAL_MAX_WORDS = 2     # a gap stub like "We hold [NEEDS FIRM INPUT: x]" leaves 1 word ("hold"); a real extra claim leaves more

# Number words count as figures: "We clean forty schools [gap]" is a claim, as "40 schools" would be.
NUMBER_WORDS = frozenset("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
                         "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand "
                         "million billion dozen dozens hundreds thousands millions none single double twice once half".split())
# Negations state a fact ("no incidents", "never had a breach"), so they also keep a gap sentence a claim.
NEGATIONS = frozenset("no not never nil nothing nobody neither nor without".split())
_ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]{1,}\b")
# A letter+digit code ("S1", "H2", "A4") is a reference or a standard, so it is a figure like a digit. The digit check on the
# residual already holds for these; the explicit pattern keeps it so if that check is ever narrowed.
_CODE = re.compile(r"\b[A-Za-z]+\d+[A-Za-z0-9]*\b|\b\d+[A-Za-z]+[A-Za-z0-9]*\b")
# Contracted and fused negations. _norm splits "n't" into two tokens, so they are matched on the raw sentence.
_NEG_RAW = re.compile(r"\bcannot\b|\bcant\b|n['\u2019]t\b", re.IGNORECASE)
# Assertion words that make a claim on their own: a sole one of these ("We are compliant [gap]") is a claim, not a stub.
# A hyphenated compound ("incident-free", "award-winning") is also a claim (_HYPHEN), whatever its parts.
CLAIM_WORDS = frozenset("free compliant compliance accredited accreditation certified certification approved vetted qualified "
                        "registered licensed licenced insured guaranteed guarantee award awarded winning proven safe secure "
                        "safeguarded trained checked audited won best leading trusted experienced".split())
_HYPHEN = re.compile(r"\w[-\u2010\u2011]\w")


def gap_residual(sentence: str) -> str:
    """The non-connective words left of a gap sentence once the [NEEDS FIRM INPUT: ...] markers and [E-n] are removed."""
    rest = _norm(_CITE.sub(" ", _GAP.sub(" ", sentence)))
    return " ".join(w for w in rest.split() if w not in CONNECTIVES)


def carries_other_content(sentence: str) -> bool:
    """True if a gap sentence says more than that it does not know. With the marker(s) and [E-n] stripped, any of these
    keeps it a claim: a digit or letter+digit code (S1); a claim word (compliant, accredited, certified, free, ...) or hyphenated
    compound (incident-free); cannot or n't; a number word (forty, zero, ...); a negation (no, not, never, nil, ...); an acronym (ISO, RIDDOR); the app's own claimcheck
    fact_triggers firing (codes, pound, percent, a run of capitalised words such as "Cyber Essentials"); or more than
    RESIDUAL_MAX_WORDS non-connective words. So "We hold [gap]" stays exempt, while "Our team cleaned schools [gap]",
    "We are ISO certified [gap]" and "zero RIDDOR incidents [gap]" are claims (T-202 review must-fix)."""
    from app.tender.claimcheck import fact_triggers
    rest = gap_residual(sentence)
    words = rest.split()
    stripped = _CITE.sub(" ", _GAP.sub(" ", sentence))
    return (any(ch.isdigit() for ch in rest) or any(w in NUMBER_WORDS or w in NEGATIONS or w in CLAIM_WORDS for w in words)
            or bool(_CODE.search(stripped)) or bool(_NEG_RAW.search(stripped)) or bool(_HYPHEN.search(stripped))
            or bool(_ACRONYM.search(stripped)) or bool(fact_triggers(sentence, 0, len(sentence)))
            or len(words) > RESIDUAL_MAX_WORDS)


def split_claims(text: str) -> tuple[list[str], list[str]]:
    """(claims, exempt gap sentences). A4 claims are the app's sentences (a citation after the full stop stays with its
    sentence, a gap marker stays whole). A sentence with a [NEEDS FIRM INPUT: ...] marker and no [E-n] is exempt (the draft
    is saying it does not know, which A8 rewards) only if carries_other_content is false for it (see that function and the EVAL.md
    A4 row for the full trigger list). A gap sentence with more content, such as "We hold 40 contracts and [NEEDS FIRM
    INPUT: insurer] cover.", stays a claim and fails A4 without a citation. A gap sentence that cites is always scored."""
    claims, exempt = [], []
    for s in split_sentences(text):
        if _GAP.search(s) and not _CITE.search(s):
            if carries_other_content(s):
                claims.append(s)
            else:
                exempt.append(s)
            continue
        if not _norm(_CITE.sub(" ", _GAP.sub(" ", s))):
            continue
        claims.append(s)
    return claims, exempt


def claims_of(text: str) -> list[str]:
    return split_claims(text)[0]


def score_traceability(drafts: list[dict]) -> dict:
    """A4. drafts: [{"id", "text", "retrieved_ids", "live_ids"}]. A claim passes if it carries at least one [E-n] and every
    [E-n] in it is both a live passage of the tenant and in that draft's retrieved set."""
    total = ok = n_sentences = 0
    exempt_all = []
    failures = []
    for d in drafts:
        live, retrieved = set(d.get("live_ids", [])), set(d.get("retrieved_ids", []))
        claims, exempt = split_claims(d["text"])
        exempt_all += exempt
        n_sentences += len(claims) + len(exempt)
        for claim in claims:
            total += 1
            ids = [int(n) for n in _CITE.findall(claim)]
            if ids and all(n in live and n in retrieved for n in ids):
                ok += 1
            else:
                failures.append({"draft": d["id"], "claim": claim, "reason": "no citation" if not ids else "does not resolve"})
    s = _ratio(ok, total)
    return {"score": s, "claims": total, "resolved": ok, "pass": s is not None and s >= BARS["A4"], "failures": failures,
            "gap_exempt": len(exempt_all), "gap_exempt_share": _ratio(len(exempt_all), n_sentences), "gap_exempt_sentences": exempt_all}


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


COVER_MIN = 0.5       # share of the seeded claim's word tokens the checker span must contain
SHARE_MIN = 0.3       # the seeded claim must be at least this share of the checker span's tokens (unless same sentence)


def _tokens(s: str) -> list[str]:
    return _norm(s).split()


def _contains(seq: list[str], sub: list[str]) -> bool:
    n = len(sub)
    return n > 0 and any(seq[i:i + n] == sub for i in range(len(seq) - n + 1))


def _overlaps(checker_span: str, seeded_span: str, sentences: tuple[list[str], ...] = ()) -> bool:
    """A6a overlap, pre-registered in EVAL.md. On word tokens (never raw characters): the checker span must cover at least
    50% of the seeded span's distinct tokens AND either the seeded span is at least 30% of the checker span's tokens, or both
    spans sit inside one app sentence of the draft (`sentences`: each sentence's tokens). A tiny span or a whole-paragraph
    span therefore misses."""
    c, s = _tokens(checker_span), _tokens(seeded_span)
    if not c or not s:
        return False
    cover = len(set(c) & set(s)) / len(set(s))
    if cover < COVER_MIN:
        return False
    if len(s) >= SHARE_MIN * len(c):
        return True
    return any(_contains(sent, c) and _contains(sent, s) for sent in sentences)


def score_seeded_claims(seeded: list[dict], checked: list[dict], draft_texts: dict | None = None) -> dict:
    """A6a. seeded: [{"id", "draft", "type", "span"}]; checked: [{"draft", "span", "verdict"}] from the claim check run on
    the fixture drafts; draft_texts: {draft id: text}, which enables the same-sentence arm of the overlap rule. A seeded claim
    is caught when a checker claim on the same draft passes `_overlaps` with verdict unsupported or contradicted. `unchecked`
    and `supported` are misses. `false_flags` reports how often the checker flagged a claim that overlaps no seeded claim, so
    a checker that flags everything is visible next to a high A6a."""
    draft_texts = draft_texts or {}
    sents = {d: tuple(_tokens(x) for x in split_sentences(t)) for d, t in draft_texts.items()}
    by_draft = defaultdict(list)
    for c in checked:
        by_draft[c["draft"]].append(c)
    flagged = ("unsupported", "contradicted")
    caught, misses, per_type = 0, [], defaultdict(lambda: [0, 0])
    for s in seeded:
        hit = any(c["verdict"] in flagged and _overlaps(c["span"], s["span"], sents.get(s["draft"], ()))
                  for c in by_draft.get(s["draft"], []))
        per_type[s["type"]][1] += 1
        if hit:
            caught += 1; per_type[s["type"]][0] += 1
        else:
            misses.append({"id": s["id"], "type": s["type"], "draft": s["draft"], "span": s["span"]})
    non_seeded = false_flags = 0
    for c in checked:
        if any(s["draft"] == c["draft"] and _overlaps(c["span"], s["span"], sents.get(c["draft"], ())) for s in seeded):
            continue
        non_seeded += 1
        false_flags += c["verdict"] in flagged
    total = len(seeded)
    return {"caught": caught, "total": total, "score": _ratio(caught, total),
            "pass": total > 0 and caught / total >= BARS["A6a"],
            "per_type": {t: {"caught": c, "total": n} for t, (c, n) in sorted(per_type.items())}, "misses": misses,
            "false_flags": {"flagged": false_flags, "non_seeded_claims": non_seeded, "rate": _ratio(false_flags, non_seeded)}}


# ---------- retrieval diagnostic (DESIGN 4.2 "Retrieval check", T-206): no bar, never part of BARS or `pass` ----------

def retrieval_recall(labels: dict, retrieved: dict, k: int = 8) -> dict:
    """Recall@k of the app's retrieval against qa's hand labels (eval/keys/retrieval_labels.json).

    labels    : {"packs": {pack: [{"ref", "relevant": [E...], "primary": [E...], ...}]}}
    retrieved : {pack: {ref: [display numbers, best first]}}; only the first k count. A question absent from it counts
                recall 0 (and primary miss) and is listed. A gap question (empty `relevant`) has no recall; it only
                records whether anything was retrieved (informational).
    Reports per pack and pooled: mean recall over questions with a non-empty `relevant`, primary hit rate over the same
    questions that have a `primary`, gap counts, and the misses (a question with any relevant passage outside the top k).
    """
    per_pack, misses = {}, []
    pooled = {"recalls": [], "primary": [], "gap": 0, "gap_retrieved": 0}
    for pack, items in (labels.get("packs") or {}).items():
        rec, prim, gap, gap_ret = [], [], 0, 0
        for it in items:
            ref = it["ref"]
            relevant = [int(x) for x in it.get("relevant") or []]
            got = (retrieved.get(pack) or {}).get(ref)
            top = {int(x) for x in (got or [])[:k]}
            if not relevant:
                gap += 1
                gap_ret += 1 if top else 0
                continue
            hit = [e for e in relevant if e in top]
            rec.append(len(hit) / len(relevant))
            primary = [int(x) for x in it.get("primary") or []]
            if primary:
                prim.append(any(e in top for e in primary))
            missing = [e for e in relevant if e not in top]
            if missing:
                misses.append({"pack": pack, "ref": ref, "missing": missing, "not_retrieved": got is None})
        per_pack[pack] = {"questions": len(items), "scored": len(rec), "recall": _ratio(sum(rec), len(rec)),
                          "primary_hit_rate": _ratio(sum(prim), len(prim)), "gap_questions": gap,
                          "gap_retrieved_anything": gap_ret}
        pooled["recalls"] += rec
        pooled["primary"] += prim
        pooled["gap"] += gap
        pooled["gap_retrieved"] += gap_ret
    return {"k": k, "per_pack": per_pack,
            "pooled": {"scored": len(pooled["recalls"]), "recall": _ratio(sum(pooled["recalls"]), len(pooled["recalls"])),
                       "primary_hit_rate": _ratio(sum(pooled["primary"]), len(pooled["primary"])),
                       "gap_questions": pooled["gap"], "gap_retrieved_anything": pooled["gap_retrieved"]},
            "misses": misses}
