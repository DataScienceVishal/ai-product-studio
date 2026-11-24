import json
import re
import sys
from collections import Counter
from pathlib import Path

import jsonschema
import pytest
from pypdf import PdfReader

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))
import generate  # noqa: E402

SCHEMA = json.loads((BENCH / "truth.schema.json").read_text())


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("gen")
    manifest = generate.generate(d)
    return d, manifest


def truths(d, sub):
    return [json.loads(p.read_text()) for p in sorted((d / sub).glob("*.json"))]


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def test_determinism(out, tmp_path):
    d, _ = out
    generate.generate(tmp_path)
    for sub in ("truth", "tuning_truth"):
        for p in (d / sub).glob("*.json"):
            assert p.read_text() == (tmp_path / sub / p.name).read_text()
    assert (d / "manifest.json").read_text() == (tmp_path / "manifest.json").read_text()


def test_different_seed_differs(out, tmp_path):
    d, _ = out
    generate.generate(tmp_path, seed=1)
    assert (d / "truth/S011.json").read_text() != (tmp_path / "truth/S011.json").read_text()


def test_all_truth_validates(out):
    d, _ = out
    for sub in ("truth", "tuning_truth"):
        for t in truths(d, sub):
            jsonschema.validate(t, SCHEMA)


def test_counts_and_mix(out):
    d, m = out
    ts = truths(d, "truth")
    assert len(ts) == 30 and len(list((d / "sheets").glob("*.pdf"))) == 30
    assert Counter(t["tier"] for t in ts) == {"clean": 10, "moderate": 10, "messy": 10}
    layouts = Counter(t["layout"] for t in ts)
    for lay in ("table", "prose", "scanned", "mixed_units", "multi_component", "missing_fields", "contradictory"):
        assert layouts[lay] > 0, lay
    assert sorted(m["messiest_10"]) == sorted(t["sheet_id"] for t in ts if t["tier"] == "messy")
    assert len(m["messiest_10"]) == 10
    comps = [len(t["components"]) for t in ts]
    assert max(comps) >= 4 and min(comps) == 1
    statuses = Counter()
    for t in ts:
        for c in t["components"]:
            for f in ("material", "colour", "weight_g"):
                statuses[c[f]["status"]] += 1
    assert statuses["missing"] > 0 and statuses["conflict"] > 0
    # clean tier: single component, all present
    for t in ts:
        if t["tier"] == "clean":
            assert len(t["components"]) == 1
            assert all(t["components"][0][f]["status"] == "present" for f in ("material", "colour", "weight_g"))
    # units: oz, kg and mg shown somewhere in the test set
    text = " ".join(" ".join(PdfReader(p).pages[i].extract_text() or "" for i in range(len(PdfReader(p).pages)))
                    for p in (d / "sheets").glob("*.pdf") if t_is_text(d, p))
    for u in (" oz", " kg", " mg"):
        assert u in text


def t_is_text(d, p):
    return not next(x for x in json.loads((d / "manifest.json").read_text())["test"]
                    if x["sheet_id"] == p.stem)["scanned"]


def test_tuning_set_separate(out):
    d, m = out
    assert len(m["tuning"]) == 5
    ids = {x["sheet_id"] for x in m["tuning"]}
    assert not ids & {x["sheet_id"] for x in m["test"]}
    assert all(t["seed"] == generate.TUNING_SEED for t in truths(d, "tuning_truth"))
    assert all(t["seed"] == generate.SEED for t in truths(d, "truth"))


def iter_values(t):
    for c in t["components"]:
        for f in ("material", "colour", "weight_g"):
            yield f, c[f]
        for k, v in c["features"].items():
            yield k, v


def test_every_quote_on_stated_page_text_sheets(out):
    d, m = out
    checked = 0
    for sub_pdf, sub_truth, rows in (("sheets", "truth", m["test"]), ("tuning", "tuning_truth", m["tuning"])):
        for row in rows:
            if row["scanned"]:
                continue
            sid = row["sheet_id"]
            t = json.loads((d / sub_truth / f"{sid}.json").read_text())
            reader = PdfReader(d / sub_pdf / f"{sid}.pdf")
            assert len(reader.pages) == row["pages"]
            pages = [norm(p.extract_text()) for p in reader.pages]
            for name, fld in iter_values(t):
                if fld["status"] == "missing":
                    assert "refs" not in fld
                    continue
                for ref in fld["refs"]:
                    assert 1 <= ref["page"] <= len(pages), (sid, name)
                    assert norm(ref["quote"]) in pages[ref["page"] - 1], (sid, name, ref)
                    checked += 1
    assert checked > 100


def test_quotes_contain_value_or_accepted(out):
    d, _ = out
    for t in truths(d, "truth") + truths(d, "tuning_truth"):
        for name, fld in iter_values(t):
            if fld["status"] == "present" and isinstance(fld["value"], str):
                cands = [fld["value"]] + fld.get("accepted_values", [])
                q = norm(fld["refs"][0]["quote"])
                assert any(norm(c) in q for c in cands), (t["sheet_id"], name, fld)
            if fld["status"] == "conflict":
                assert len(fld["conflict_values"]) == 2 and len(fld["refs"]) == 2
                assert len({r["page"] for r in fld["refs"]}) == 2


def test_weights_match_displayed_units(out):
    d, _ = out
    for t in truths(d, "truth"):
        for c in t["components"]:
            w = c["weight_g"]
            if w["status"] != "present":
                continue
            q = w["refs"][0]["quote"]
            num, unit = q.split()
            factor = {"g": 1, "kg": 1000, "mg": 0.001, "oz": generate.G_PER_OZ}[unit]
            assert abs(float(num) * factor - w["value"]) <= max(0.1, 0.01 * w["value"])


def test_scanned_sheets_are_images(out):
    d, m = out
    scanned = [r for r in m["test"] if r["scanned"]]
    assert len(scanned) == 5
    for r in scanned:
        reader = PdfReader(d / "sheets" / f"{r['sheet_id']}.pdf")
        assert not any((p.extract_text() or "").strip() for p in reader.pages)
        assert len(reader.pages) == r["pages"]


def test_total_size_under_limit(out):
    d, _ = out
    assert sum(p.stat().st_size for p in d.rglob("*") if p.is_file()) < 15 * 1024 * 1024
