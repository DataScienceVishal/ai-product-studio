import json
from pathlib import Path

import pytest

import generate as g

DATA = Path(__file__).resolve().parents[1] / "data"


def test_generation_is_deterministic(tmp_path):
    a = g.generate_set("dev", tmp_path / "a", images=False)
    b = g.generate_set("dev", tmp_path / "b", images=False)
    assert g.truth_digest(a) == g.truth_digest(b)
    for p in sorted((tmp_path / "a" / "dev").glob("*")):
        assert p.read_bytes() == (tmp_path / "b" / "dev" / p.name).read_bytes()  # truth JSON and PDFs are byte-identical


def test_committed_dev_manifest_matches_files():
    assert g.verify_manifest(DATA / "dev") == []


def test_images_are_deterministic(tmp_path):
    a = g.generate_set("dev", tmp_path / "a")
    g.generate_set("dev", tmp_path / "b")
    assert json.loads((tmp_path / "a" / "dev" / "MANIFEST.json").read_text()) == \
        json.loads((tmp_path / "b" / "dev" / "MANIFEST.json").read_text())
    assert len(a) == 10


def test_seeds():
    assert (g.DEV_SEED, g.TEST_SEED) == (1001, 2025)


def test_dev_set_shape():
    plan = g.DEV_PLAN
    assert len(plan) == 10
    assert {p[0] for p in plan} == set(g.DEV_LAYOUTS)  # dev layouts only
    assert sum(p[1] for p in plan) >= 1 and sum(p[3] for p in plan) >= 1


def test_ground_truth_arithmetic_and_fields(tmp_path):
    invs = g.generate_set("dev", tmp_path, images=False)
    for inv in invs:
        g.check_totals(inv)
        assert inv["layout"] in g.DEV_LAYOUTS and inv["heldout"] is False
        assert all(ln["page"] <= inv["pages"] for ln in inv["lines"])
        assert {"description", "qty", "pack_size", "unit", "unit_price", "line_total", "vat_rate"} <= set(inv["lines"][0])
        if inv["credit_note"]:
            assert all(ln["qty"] < 0 and ln["line_total"] < 0 for ln in inv["lines"])
            assert inv["totals"]["gross"] < 0
    assert any(len({ln["vat_rate"] for ln in i["lines"]}) >= 2 for i in invs)  # mixed VAT
    assert any(i["credit_note"] for i in invs) and any(i["pages"] > 1 for i in invs)


def test_distortion_parameters_are_logged_and_in_range():
    for f in DATA.glob("dev/DEV-*.json"):
        t = json.loads(f.read_text())
        assert bool(t["distortion"]) == t["distorted"]
        for d in t["distortion"]:
            assert 2 <= abs(d["rotation_deg"]) <= 12 and 0.5 <= d["blur_sigma"] <= 1.5 and 35 <= d["jpeg_quality"] <= 70


def test_test_plan_meets_the_kill_test_mix():
    plan = g.test_plan()
    assert len(plan) == 50
    assert sum(1 for p in plan if p[0] in g.DEV_LAYOUTS) == 25
    assert sum(1 for p in plan if p[0] in g.HELDOUT_LAYOUTS) == 25
    assert sum(p[2] for p in plan) == 30
    assert sum(p[1] for p in plan) >= 8
    assert sum(p[3] for p in plan) >= 10


def test_test_set_refused_until_heldout_layouts_exist(tmp_path):
    if g.load_heldout():
        pytest.skip("held-out layouts exist")
    with pytest.raises(SystemExit):
        g.generate_set("test", tmp_path, images=False)
