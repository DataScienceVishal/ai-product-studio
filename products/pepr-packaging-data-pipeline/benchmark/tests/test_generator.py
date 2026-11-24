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
import taxonomy as tx  # noqa: E402

SCHEMA = json.loads((BENCH / "truth.schema.json").read_text())
norm = tx.norm_text


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("gen")
    manifest = generate.generate(d)
    return d, manifest


def truths(d, sub):
    return [json.loads(p.read_text()) for p in sorted((d / sub).glob("*.json"))]


def all_files(d):
    return {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}


def iter_values(t):
    for c in t["components"]:
        for f in ("material", "colour", "weight_g"):
            yield f, c[f]
        for k, v in c["features"].items():
            yield k, v


def page_texts(d, sub_pdf, row):
    """Text per page: PDF text layer for text sheets, recorded page text for image-only sheets."""
    if row["scanned"]:
        return [norm(t) for t in row["page_text"]]
    reader = PdfReader(d / sub_pdf / f"{row['sheet_id']}.pdf")
    assert len(reader.pages) == row["pages"]
    return [norm(p.extract_text()) for p in reader.pages]


def test_byte_equal_regeneration(out, tmp_path):
    d, _ = out
    generate.generate(tmp_path)
    a, b = all_files(d), all_files(tmp_path)
    assert a.keys() == b.keys()
    for k in a:
        assert a[k] == b[k], f"{k} differs between runs"


def test_committed_data_is_current(out):
    committed = BENCH / "data"
    if not committed.exists():
        pytest.skip("no committed data")
    d, _ = out
    assert all_files(d) == all_files(committed)


def test_pdf_dates_fixed(out):
    d, _ = out
    for p in (d / "sheets").glob("*.pdf"):
        raw = p.read_bytes()
        if b"/CreationDate" in raw and b"/Producer (Pillow" in raw:
            assert b"D:20261124000000" in raw, p.name


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
    assert m["messiest_10"] == [f"S{n:03d}" for n in range(21, 31)]
    comps = [len(t["components"]) for t in ts]
    assert max(comps) >= 4 and min(comps) == 1
    for t in ts:
        if t["tier"] == "clean":
            assert len(t["components"]) == 1
            assert all(t["components"][0][f]["status"] == "present" for f in ("material", "colour", "weight_g"))
    assert len({t["template"] for t in ts}) >= 5
    assert any(f["status"] == "conflict" for t in ts if t["tier"] == "moderate" for _, f in iter_values(t))


def test_units_shown_in_text_sheets(out):
    d, m = out
    txt = ""
    for row in m["test"]:
        if not row["scanned"]:
            txt += " ".join(page_texts(d, "sheets", row))
    for u in (" oz", " kg", " mg"):
        assert u in txt


def test_tuning_set_separate(out):
    d, m = out
    assert len(m["tuning"]) == 5
    ids = {x["sheet_id"] for x in m["tuning"]}
    assert not ids & {x["sheet_id"] for x in m["test"]}
    assert all(t["seed"] == generate.TUNING_SEED for t in truths(d, "tuning_truth"))
    assert all(t["seed"] == generate.SEED for t in truths(d, "truth"))


def test_tuning_set_coverage(out):
    d, m = out
    rows = {r["sheet_id"]: r for r in m["tuning"]}
    ts = {t["sheet_id"]: t for t in truths(d, "tuning_truth")}
    layouts = {r["layout"] for r in rows.values()}
    assert {"table", "multi_component", "mixed_units", "scanned", "contradictory"} <= layouts
    clean = [t for t in ts.values() if t["tier"] == "clean"]
    assert len(clean) == 1 and len(clean[0]["components"]) == 1
    multi = ts["S902"]
    assert len(multi["components"]) >= 3
    assert any(c[f]["status"] == "missing" for c in multi["components"] for f in ("material", "colour", "weight_g"))
    units = set()
    for c in ts["S903"]["components"]:
        for r in c["weight_g"].get("refs", []):
            units.add(r["quote"].split()[-1])
    assert len(units) >= 3
    assert rows["S904"]["scanned"] and any(c["weight_g"]["status"] == "conflict" for c in ts["S904"]["components"])
    assert not rows["S905"]["scanned"] and sum(c["weight_g"]["status"] == "conflict" for c in ts["S905"]["components"]) >= 1


def test_plausible_keys_all_present_and_no_implausible(out):
    d, _ = out
    for t in truths(d, "truth") + truths(d, "tuning_truth"):
        for c in t["components"]:
            assert c["name"] in tx.PLAUSIBLE
            assert set(c["features"]) == set(tx.PLAUSIBLE[c["name"]]), (t["sheet_id"], c["name"])
            for k, f in c["features"].items():
                assert f["status"] in ("present", "missing")
                if f["status"] == "present":
                    assert f["value"] in tx.VOCAB[k], (t["sheet_id"], k, f["value"])


def test_plausible_map_is_sensible():
    assert "closure" not in tx.PLAUSIBLE["outer carton"] and "closure" not in tx.PLAUSIBLE["label"]
    assert "sleeve" not in tx.PLAUSIBLE["sleeve"]
    assert tx.PLAUSIBLE["cap"] == ["liner", "ink_coating"]
    for name, keys in tx.PLAUSIBLE.items():
        assert set(keys) <= set(tx.VOCAB) and len(keys) >= 2
    for k, vals in tx.VOCAB.items():
        for canon, paras in vals.items():
            assert len(paras) >= 2 and all(len(p) <= 30 for p in paras + [canon])


def test_conflict_count_and_missing_counts(out):
    d, m = out
    st = m["stats"]["test"]
    assert st["conflict_slots"] >= 20
    assert st["components"] == sum(len(t["components"]) for t in truths(d, "truth"))
    assert st["missing_slots"] > 100 and st["carbon_black_components"] >= 5
    feat_missing = sum(1 for t in truths(d, "truth") for c in t["components"]
                       for f in c["features"].values() if f["status"] == "missing")
    assert feat_missing > 50


def test_every_quote_on_stated_page(out):
    d, m = out
    checked = 0
    for sub_pdf, sub_truth, rows in (("sheets", "truth", m["test"]), ("tuning", "tuning_truth", m["tuning"])):
        for row in rows:
            sid = row["sheet_id"]
            t = json.loads((d / sub_truth / f"{sid}.json").read_text())
            pages = page_texts(d, sub_pdf, row)
            for name, fld in iter_values(t):
                if fld["status"] == "missing":
                    assert "refs" not in fld
                    continue
                for ref in fld["refs"]:
                    assert 1 <= ref["page"] <= len(pages), (sid, name)
                    assert norm(ref["quote"]) in pages[ref["page"] - 1], (sid, name, ref)
                    checked += 1
    assert checked > 200


def test_image_only_sheets_have_page_text(out):
    d, m = out
    scanned = [r for r in m["test"] + m["tuning"] if r["scanned"]]
    assert len([r for r in m["test"] if r["scanned"]]) == 5 and len(scanned) == 6
    for r in scanned:
        assert len(r["page_text"]) == r["pages"] and all(len(x) > 50 for x in r["page_text"])
        sub = "sheets" if r["sheet_id"] < "S900" else "tuning"
        reader = PdfReader(d / sub / f"{r['sheet_id']}.pdf")
        assert not any((p.extract_text() or "").strip() for p in reader.pages)
        assert len(reader.pages) == r["pages"]
    for r in m["test"] + m["tuning"]:
        if not r["scanned"]:
            assert "page_text" not in r


def test_quotes_contain_value_unit_parsed(out):
    d, _ = out
    for t in truths(d, "truth") + truths(d, "tuning_truth"):
        for name, fld in iter_values(t):
            if name == "weight_g" and fld["status"] == "conflict":
                assert len(fld["conflict_values"]) == 2 and len(fld["refs"]) == 2
                for v, r in zip(fld["conflict_values"], fld["refs"]):
                    assert tx.quote_ok("weight_g", v, r["quote"]), (t["sheet_id"], fld)
                assert not tx.weight_within(*fld["conflict_values"])
            elif fld["status"] == "present":
                assert tx.quote_ok(name, fld["value"], fld["refs"][0]["quote"]), (t["sheet_id"], name, fld)


def test_generator_displays_are_listed_variants():
    for name, mats in generate.COMPONENTS.items():
        for value, ram, displays in mats:
            assert value in tx.MATERIAL_VOCAB, value
            for disp in displays:
                assert disp in tx.MATERIAL_VOCAB[value], (name, value, disp)
    for value, displays in generate.COLOURS.items():
        for disp in displays:
            assert disp in tx.COLOUR_VOCAB[value], (value, disp)
    # a wording belongs to exactly one canonical value, per key
    for key in ("material", "colour") + tuple(tx.VOCAB):
        seen = {}
        for canon, words in tx.key_vocab(key).items():
            for w in words:
                assert seen.setdefault(tx.norm_text(w), canon) == canon, (key, w)


def test_every_present_material_colour_quote_has_listed_variant(out):
    d, _ = out
    n = 0
    for t in truths(d, "truth") + truths(d, "tuning_truth"):
        for c in t["components"]:
            for key in ("material", "colour"):
                f = c[key]
                if f["status"] == "present":
                    q = tx.norm_text(f["refs"][0]["quote"])
                    words = [tx.norm_text(w) for w in tx.key_vocab(key)[f["value"]]]
                    assert q in words, (t["sheet_id"], key, f)
                    assert set(f.get("accepted_values", [])) == set(tx.key_vocab(key)[f["value"]]) - {f["value"]}
                    n += 1
    assert n > 100


def test_quote_ok_rules():
    ok, bad = tx.quote_ok, lambda *a, **k: not tx.quote_ok(*a, **k)
    assert ok("material", "PET", "PET (virgin)") and bad("material", "PET", "PETG")
    assert ok("material", "PETG", "PET-G") and bad("material", "PET", "recycled PET") and ok("material", "rPET", "recycled PET")
    assert ok("colour", "black (carbon black)", "CB black") and bad("colour", "black", "CB black")
    assert ok("colour", "black", "Shade: jet black") and bad("colour", "black (carbon black)", "black")
    assert bad("material", "PET", "PET / HDPE")  # two canonical values in one quote
    assert ok("closure", "HDPE cap with PE liner", "Cap fitted: HDPE cap, PE wad liner")
    assert ok("ink_coating", "water-based varnish", "Please note aqueous varnish on this item.")
    assert bad("ink_coating", "UV-cured ink", "aqueous varnish")
    assert ok("weight_g", 159.5, "Nett wt 159500 mg (1)") and bad("weight_g", 24.0, "26 g")
    assert bad("material", "PP", "PP film", page_text="a\nPP cap")  # not on the page
    assert ok("material", "PP", "PP film | x", page_text="a\nPP film  x")  # '|' counts as whitespace
    assert ok("material", "PP", "PP film", page_text="1 | bottle | PP film | 2 g")
    assert tx.canonical("material", "BOPP") == "PP" and tx.canonical("colour", "black") == "black"
    assert tx.canonical("material", "PP blend") is None


def _row_lines(page_text_raw):
    return [ln for ln in page_text_raw.split("\n") if ln.strip()]


def test_quote_ok_whole_row_quotes_text_and_scanned(out):
    d, m = out
    checked = {"text": 0, "scanned": 0}
    for sub_pdf, sub_truth, rows in (("sheets", "truth", m["test"]), ("tuning", "tuning_truth", m["tuning"])):
        for row in rows:
            sid = row["sheet_id"]
            if row["scanned"]:
                raw = row["page_text"]
            elif row["template"] in ("table", "matrix", "bom", "prose"):
                raw = [p.extract_text() for p in PdfReader(d / sub_pdf / f"{sid}.pdf").pages]
            else:
                continue
            t = json.loads((d / sub_truth / f"{sid}.json").read_text())
            for name, fld in iter_values(t):
                if fld["status"] != "present":
                    continue
                ref = fld["refs"][0]
                page = raw[ref["page"] - 1]
                pat = re.compile(r"(?<![a-z0-9-])" + re.escape(norm(ref["quote"])) + r"(?![a-z0-9-])")
                lines = [ln for ln in _row_lines(page) if pat.search(tx.norm_quote(ln))]
                if row["scanned"]:
                    lines = [ln for ln in lines if " | " in ln]  # whole table rows
                if not lines:
                    continue
                for ln in lines:
                    assert tx.quote_ok(name, fld["value"], ln, page), (sid, name, ln)
                checked["scanned" if row["scanned"] else "text"] += 1
    assert checked["text"] > 60 and checked["scanned"] > 10, checked


def test_ram_category_scored_only_when_material_present(out):
    d, _ = out
    for t in truths(d, "truth"):
        slots = list(tx.scored_slots(t))
        for i, c in enumerate(t["components"]):
            has = any(s == "ram_category" and ci == i for ci, s, _ in slots)
            assert has == (c["material"]["status"] != "missing")


def test_synonyms_and_distractors_make_it_harder(out):
    d, m = out
    text = " ".join(" ".join(page_texts(d, "sheets", r)) for r in m["test"] if not r["scanned"])
    for needle in ("resin", "substrate", "nett wt", "mass", "shade", "polymer", "tint", "gross weight", "pallet weight",
                   "wall thickness", "case count", "cap torque", "n/a", "tbc", "to be confirmed"):
        assert needle in text, needle
    diff = tot = 0
    for t in truths(d, "truth"):
        if t["tier"] == "clean":
            continue
        for name, f in iter_values(t):
            if name in tx.VOCAB and f["status"] == "present":
                tot += 1
                diff += norm(f["refs"][0]["quote"]) != norm(f["value"])
    assert tot > 30 and diff == tot
    modes = Counter(x for r in m["test"] for x in r["conflict_modes"])
    assert modes["footnote"] > 0 and modes["notes"] > 0
    assert any(r["template"] == "prose_buried" and r["tier"] == "messy" for r in m["test"])


def test_absent_rows_instead_of_dash(out):
    d, m = out
    for row in m["test"]:
        if not row["scanned"]:
            txt = " | ".join(page_texts(d, "sheets", row))
            assert "| - |" not in txt


def test_weight_and_name_normalisation():
    assert tx.norm_name("Shipper Carton") == "outer carton" and tx.norm_name("sachet") == "pouch"
    assert abs(tx.parse_weight("0.370 oz") - 10.49) < 0.01 and tx.parse_weight("159500 mg") == 159.5
    assert tx.weight_within(24.05, 24.0) and not tx.weight_within(26.0, 24.0)


def test_total_size_under_limit(out):
    d, _ = out
    assert sum(p.stat().st_size for p in d.rglob("*") if p.is_file()) < 5 * 1024 * 1024


def test_amendment3_gram_spellings_parse():
    for q in ("37.00gm", "37.00 gm \u00b1 2.00gm", "37 gms", "37 grams", "37 gram", "37g"):
        assert tx.parse_weight(q) == 37.0, q
    assert tx.parse_weight("0.037 kg") == 37.0 and tx.parse_weight("37 gsm") is None  # areal weight is not unit weight
