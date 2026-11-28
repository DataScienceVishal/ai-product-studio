"""T-196: the pre-registered eval keys (eval/keys/). Schema and count checks, and a recompute of the [E-n] numbering with the
app's own parser and chunker, so a change to the evidence library or the chunker fails loudly. No model, no DB use."""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

PRODUCT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PRODUCT))

from app.tender.chunking import chunk_pages  # noqa: E402
from app.tender.ingest import run_worker  # noqa: E402
from eval import seed as SD  # noqa: E402

KEYS = PRODUCT / "eval" / "keys"


def load(name):
    return json.loads((KEYS / name).read_text(encoding="utf-8"))


def words(s):
    return set(re.findall(r"[a-z0-9£]+", s.lower()))


def test_trap_sets():
    trap, dev = load("trap_set.json"), load("dev_trap_set.json")
    assert len(trap) == 30 and len(dev) == 10
    assert [t["id"] for t in trap] == [f"TR{i:02d}" for i in range(1, 31)]
    assert [t["id"] for t in dev] == [f"DT{i:02d}" for i in range(1, 11)]
    for t in trap + dev:
        assert set(t) == {"id", "question", "word_limit", "trap", "why"}
        assert t["trap"] in ("missing", "partial")
        assert t["word_limit"] is None or (isinstance(t["word_limit"], int) and t["word_limit"] > 0)
        assert t["question"].strip() and ".md" in t["why"] or "library" in t["why"]
    c = Counter(t["trap"] for t in trap)
    assert c["missing"] == 20 and c["partial"] == 10
    qs = [t["question"].lower() for t in trap + dev]
    assert len(set(qs)) == 40
    for d in dev:
        for t in trap:
            a, b = words(d["question"]), words(t["question"])
            assert len(a & b) / len(a | b) < 0.5, (d["id"], t["id"])
    for t in trap + dev:  # every evidence file named in a "why" exists
        for f in re.findall(r"\b\d\d-[a-z0-9-]+\.md", t["why"]):
            assert (PRODUCT / "demo-data" / "evidence" / f).is_file(), (t["id"], f)


def test_drafts_and_seeded_claims():
    drafts, claims = load("fixture_drafts.json"), load("seeded_claims.json")
    assert len(drafts) == 20 and len(claims) == 40
    assert [d["id"] for d in drafts] == [f"F{i:02d}" for i in range(1, 21)]
    assert [c["id"] for c in claims] == [f"S{i:02d}" for i in range(1, 41)]
    by_id = {d["id"]: d for d in drafts}
    for d in drafts:
        assert set(d) == {"id", "question", "text", "retrieved_ids"}
        assert 80 <= len(d["text"].split()) <= 200, d["id"]
        cited = {int(n) for n in re.findall(r"\[E-(\d+)\]", d["text"])}
        assert cited and cited <= set(d["retrieved_ids"]), d["id"]
        assert d["retrieved_ids"] == sorted(set(d["retrieved_ids"]))
    assert Counter(c["draft"] for c in claims) == {d["id"]: 2 for d in drafts}
    for c in claims:
        assert set(c) == {"id", "draft", "type", "span"}
        assert c["type"] in ("number", "client", "accreditation", "date")
        text = by_id[c["draft"]]["text"]
        assert text.count(c["span"]) == 1, c["id"]
        assert 4 <= len(c["span"].split()) <= 20 and "[E-" not in c["span"], c["id"]
    t = Counter(c["type"] for c in claims)
    assert set(t) == {"number", "client", "accreditation", "date"} and all(8 <= n <= 12 for n in t.values()), t
    spans = [c["span"] for c in claims]
    assert len(set(spans)) == 40


def _numbering():
    docs = SD.evidence_docs(SD.EVIDENCE_DIR)  # seed.py's upload order (README.md skipped)
    out, n = {}, 1
    for d in docs:
        res = run_worker("txt", d.read_bytes(), 500)
        assert res["ok"], d.name
        for i, p in enumerate(chunk_pages(res["pages"]), start=1):
            out[n] = (d.name, i, p.text)
            n += 1
    return out


def test_evidence_map_matches_app_chunker():
    emap, nums = load("evidence_map.json"), _numbering()
    assert emap["total_passages"] == len(nums)
    entries = emap["entries"]
    assert [e["e"] for e in entries] == sorted({e["e"] for e in entries})
    used = {i for d in load("fixture_drafts.json") for i in d["retrieved_ids"]}
    assert used == {e["e"] for e in entries}
    for e in entries:
        name, idx, text = nums[e["e"]]
        assert (e["file"], e["passage_index"]) == (name, idx), e["e"]
        assert e["sha256"] == hashlib.sha256(text.encode()).hexdigest(), f"E-{e['e']} text changed"
        assert e["first80"] == text[:80]
    assert all(not e["file"].startswith("README") for e in entries)  # no key relies on the README passages


def test_seed_skips_readme():
    assert "README.md" not in {p.name for p in SD.evidence_docs(SD.EVIDENCE_DIR)}
    assert len(SD.evidence_docs(SD.EVIDENCE_DIR)) == 32
