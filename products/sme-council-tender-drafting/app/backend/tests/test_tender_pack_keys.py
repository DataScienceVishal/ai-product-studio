"""Structural checks on the hand-written tender pack answer keys (eval/keys/S*.json). No database, no model."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
KEYS = sorted((ROOT / "eval" / "keys").glob("S*.json"))
MANIFEST = json.loads((ROOT / "demo-data" / "packs" / "manifest.json").read_text())

# Quality + social value total for the questions in each pack (percent of tender score).
QUALITY_TOTAL = {
    "S01": 70,  # pack-source S01 l.~324: "Total available weighting for Section 5: 70 percent"
    "S05": 60,  # S05 "Weighting check" table: Total 60%
    "S09": 70,  # S09 section 7: Quality 60% + Social value 10%
}
BASE = {"ref", "kind", "text", "word_limit", "page_limit", "marks", "weight_pct"}
EXTRA = {"case_studies", "shared_group", "shared_words"}


def _load(p):
    return json.loads(p.read_text())


def test_keys_present():
    assert KEYS, "no pack keys"


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
    assert sum(i["weight_pct"] or 0 for i in qs) == QUALITY_TOTAL[path.stem[:3]]
    assert all(i["weight_pct"] is None for i in items if i["kind"] != "question")
    deadlines = [i for i in items if i["kind"] == "deadline"]
    assert len(deadlines) == 1 and "2027" in deadlines[0]["text"] and ":" in deadlines[0]["text"]
    assert any(i["kind"] == "mandatory" for i in items)
    # shared-group members carry no per-item word limit
    for i in qs:
        if "shared_group" in i:
            assert i["word_limit"] is None and i["shared_words"]
