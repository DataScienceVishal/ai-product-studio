import json
from pathlib import Path

import generate as g

DATA = Path(__file__).resolve().parents[1] / "data"


def test_committed_test_set_matches_manifest_and_mix():
    assert g.verify_manifest(DATA / "test") == []
    truths = [json.loads(f.read_text()) for f in sorted((DATA / "test").glob("TEST-*.json"))]
    assert len(truths) == 50
    assert sum(t["heldout"] for t in truths) == 25
    assert sum(t["distorted"] for t in truths) == 30
    assert sum(t["credit_note"] for t in truths) >= 8
    assert sum(t["pages"] > 1 for t in truths) >= 10
    assert all(1 <= t["pages"] <= 3 for t in truths)
    for t in truths:
        g.check_totals(t)
    assert json.loads((DATA / "test" / "MANIFEST.json").read_text())["seed"] == 2025


def test_heldout_layouts_load_and_test_set_is_deterministic(tmp_path):
    assert g.load_heldout()
    a = g.generate_set("test", tmp_path / "a", images=False)
    b = g.generate_set("test", tmp_path / "b", images=False)
    assert g.truth_digest(a) == g.truth_digest(b)
    assert {i["layout"] for i in a} == set(g.DEV_LAYOUTS + g.HELDOUT_LAYOUTS)
