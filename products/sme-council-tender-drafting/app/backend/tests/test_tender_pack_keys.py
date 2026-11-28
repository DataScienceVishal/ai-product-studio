"""Structural checks on the hand-written tender pack answer keys (eval/keys/S*.json). No database, no model."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = json.loads((ROOT / "demo-data" / "packs" / "manifest.json").read_text(encoding="utf-8"))
# Keys are the held-out packs named in the manifest, so a missing key fails and demo-pack files never count.
KEYS = [ROOT / "eval" / "keys" / f"{Path(n).stem}.json" for n in MANIFEST["heldout"]]

# Quality + social value total for the questions in each pack (percent of tender score).
QUALITY_TOTAL = {
    "S01": 70,  # pack-source S01 .md l.396: "Total available weighting for Section 5: 70 percent"
    "S05": 60,  # S05 .md l.335 "Weighting check" table: Total 60%
    "S09": 70,  # S09 .md l.94, section 7: Quality 60% + Social value 10%
    "S02": 70,  # S02 .md l.268, Part 5 "Total quality weighting: 70%" (Part 4 award criteria: Quality 70%)
    "S03": 60,  # S03 .md l.266, Section 5 "Check: 10 + 8 + 8 + 4 + 8 + 6 + 6 + 5 + 5 = 60%"
    "S07": 70,  # S07 .md l.177, Part 6 "Total weighting is 70%"
    "S10": 60,  # S10 .md l.175 "Weighting check": Q1-Q7 50% + Q8 10%
    "S11": 70,  # S11 .md l.73, 1.5: Quality Q1-Q12 60% + social value Q13 10%
}
# Packs that score in points: sum of `marks` of the questions instead of weight_pct.
MARKS_TOTAL = {
    "S06": 60,  # S06 .md l.167, Section 6 "Total marks available for quality: 10 + 8 + 8 + 6 + 6 + 6 + 8 + 8 = 60 marks"
}
BASE = {"ref", "kind", "text", "word_limit", "page_limit", "marks", "weight_pct"}
EXTRA = {"case_studies", "shared_group", "shared_words"}


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_keys_present():
    missing = [p.name for p in KEYS if not p.is_file()]
    assert len(KEYS) == 9 and not missing, f"held-out packs without a key: {missing}"


@pytest.mark.parametrize("path", KEYS, ids=lambda p: p.stem[:3])
def test_key_names_its_own_pack(path):
    assert Path(_load(path)["pack"]).stem == path.stem


@pytest.mark.parametrize("path", KEYS, ids=lambda p: p.stem[:3])
def test_pack_key(path):
    d = _load(path)
    assert set(d) == {"pack", "items"}
    assert d["pack"] in MANIFEST["heldout"]
    assert (ROOT / "demo-data" / "packs" / d["pack"]).exists()
    assert d["pack"].startswith(path.stem[:3])
    items = d["items"]
    for it in items:
        assert BASE <= set(it) and set(it) <= BASE | EXTRA, it
        assert it["kind"] in ("question", "mandatory", "deadline"), it
        assert it["text"].strip()
        for f in ("word_limit", "page_limit", "marks", "weight_pct"):
            assert it[f] is None or (isinstance(it[f], int) and it[f] > 0), (it["ref"], f)
        if it["kind"] != "deadline":
            assert it["ref"].strip(), it
    for kind in ("question", "mandatory", "deadline"):
        refs = [i["ref"] for i in items if i["kind"] == kind]
        assert len(refs) == len(set(refs)), kind
    qs = [i for i in items if i["kind"] == "question"]
    if d["pack"] in MANIFEST["drafting_heldout"]:
        assert len(qs) >= 15
    pk = path.stem[:3]
    if pk in MARKS_TOTAL:
        assert sum(i["marks"] or 0 for i in qs) == MARKS_TOTAL[pk]
        assert all(i["weight_pct"] is None for i in items)
    else:
        assert sum(i["weight_pct"] or 0 for i in qs) == QUALITY_TOTAL[pk]
        assert all(i["marks"] is None for i in items)
    assert all(i["weight_pct"] is None and i["marks"] is None for i in items if i["kind"] != "question")
    deadlines = [i for i in items if i["kind"] == "deadline"]
    assert len(deadlines) == 1 and "2027" in deadlines[0]["text"] and ":" in deadlines[0]["text"]
    assert any(i["kind"] == "mandatory" for i in items)
    # shared-group members carry no per-item word limit
    for i in qs:
        if "shared_group" in i:
            assert i["word_limit"] is None and i["shared_words"]


def _item(stem, ref, kind="question"):
    d = _load(next(p for p in KEYS if p.stem.startswith(stem)))
    return next(i for i in d["items"] if i["ref"] == ref and i["kind"] == kind)


def test_spot_limits():
    assert _item("S07", "6")["word_limit"] == 400          # S07 .md l.211 own limit
    assert _item("S05", "Q12")["word_limit"] == 400        # S05 2.4 general rule
    assert _item("S02", "3")["word_limit"] == 500          # S02 Part 1 section 3 general rule
    assert _item("S02", "1")["word_limit"] == 750          # own limit beats the general rule
    assert _item("S09", "2.1")["word_limit"] is None       # shared 800 words, rule 7
    assert _item("S06", "Q8")["page_limit"] == 1           # S06 Q8 one side of A4
    assert _item("S10", "Q2")["word_limit"] == 350         # S10 1.3 general rule
    assert _item("S05", "Q11", "mandatory")["word_limit"] == 150
