import json
import sys
from pathlib import Path

import jsonschema
import pytest
from pypdf import PdfReader

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))
import score  # noqa: E402
import supplement  # noqa: E402
import taxonomy as tx  # noqa: E402

SCHEMA = json.loads((BENCH / "truth.schema.json").read_text())
SUPP = BENCH / "supplement"


@pytest.fixture(scope="module")
def regen(tmp_path_factory):
    d = tmp_path_factory.mktemp("supp")
    return d, supplement.generate_supplement(d)


def files(d):
    return {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}


def test_supplement_reproducible_byte_for_byte_and_committed(regen):
    d, _ = regen
    assert files(d) == files(SUPP)  # includes the AES-encrypted sheet


def test_seed_matters(tmp_path):
    supplement.generate_supplement(tmp_path, seed=1)
    assert files(tmp_path) != files(SUPP)


def test_truth_validates_and_labels_every_plausible_key():
    n = 0
    for f in sorted((SUPP / "data" / "truth").glob("S8*.json")):
        t = json.loads(f.read_text())
        jsonschema.validate(t, SCHEMA)
        n += 1
        for c in t["components"]:
            assert set(c["features"]) == set(tx.PLAUSIBLE[c["name"]])
    assert n == 12


def test_every_truth_quote_passes_quote_ok_on_its_page():
    for f in sorted((SUPP / "data" / "truth").glob("S8*.json")):
        t = json.loads(f.read_text())
        pages = [p.extract_text() or "" for p in PdfReader(str(SUPP / "data" / "sheets" / f"{t['sheet_id']}.pdf")).pages]
        for c in t["components"]:
            fields = [(k, c[k]) for k in ("material", "colour", "weight_g")] + list(c["features"].items())
            for k, fl in fields:
                for r in fl.get("refs", []):
                    assert tx.quote_ok(k, fl["value"], r["quote"], pages[r["page"] - 1], fl.get("accepted_values", [])), (t["sheet_id"], k, r)


def test_realism_items_1_to_5_covered_and_target_item():
    m = json.loads((SUPP / "manifest.json").read_text())
    assert {i for e in m["supplement"] for i in e["realism_items"]} == {1, 2, 3, 4, 5}
    cat = [e for e in m["supplement"] if e["template"] == "catalogue"]
    assert len(cat) == 1 and cat[0]["target_item"] == "PB-250-24"
    t = json.loads((SUPP / "data" / "truth" / f"{cat[0]['sheet_id']}.json").read_text())
    assert t["target_item"] == "PB-250-24"
    text = PdfReader(str(SUPP / "data" / "sheets" / f"{cat[0]['sheet_id']}.pdf")).pages[0].extract_text()
    assert text.count("PB-") + text.count("HB-") >= 6 and "Product code PB-250-24" in text
    assert [e["encrypted"] for e in m["supplement"]].count(True) == 1
    assert PdfReader(str(SUPP / "data" / "sheets" / "S812.pdf")).is_encrypted


def test_d3_areal_and_case_weights_truth_missing_and_fabrication_counted():
    t = json.loads((SUPP / "data" / "truth" / "S808.json").read_text())
    assert all(c["weight_g"]["status"] == "missing" for c in t["components"])
    pred = {"components": [{"name": c["name"], "material": c["material"], "colour": c["colour"],
                            "weight_g": {"status": "present", "value": 12400.0,
                                         "refs": [{"page": 1, "quote": "Case weight (kg) 12.4"}]},
                            "features": c["features"]} for c in t["components"]]}
    cnt = score.score_sheet(t, pred, ["Case weight (kg) 12.4"])
    assert cnt["fabricated"] == 3


# ---- Amendment 4 D1: blends ------------------------------------------------------------------------

@pytest.mark.parametrize("quote,value,ok", [
    ("rPET 30% + PET 70%", "PET", True),
    ("rPET 30% + PET 70%", "rPET", False),
    ("rPET 70% + PET 30%", "rPET", True),
    ("70% rPET / 30% PET", "rPET", True),
    ("rPET 50% + PET 50%", "PET", True),  # tie -> PET
    ("rPET 50% + PET 50%", "rPET", False),
    ("rPET + PET", "PET", False),  # no shares
    ("rPET + PET", "rPET", False),
    ("rPET 30% + PET", "rPET", False),  # one share missing
    ("rPET (PCR 100%)", "rPET", True),  # single material with recycled content is not a blend
    ("PET 100%", "PET", True),
    ("PET 70% + PETG 30%", "PET", False),  # PET/rPET family only
    ("70% rPET - 30% PET", "rPET", True),  # share-before-name with a separator
    ("70% rPET - 30% PET", "PET", False),
    ("30% rPET 70% PET", "PET", True),
    ("PET 100% | PP 100%", "PET", False),  # joined cells
    ("PET 70% + rPET 30% + HDPE 100%", "HDPE", False),  # three materials
    ("PET 70% + rPET 30% + HDPE 100%", "PET", False),
    ("PET 70% + rPET 20%", "PET", False),  # shares do not sum to 100
    ("rPET 30% + 70% PET", "PET", False),  # mixed reading directions
    ("PET 70% + rPET 30.5%", "PET", True),  # +-1 rounding
    ("HDPE 50% + PP 50%", "PP", False),  # tie without PET: no unique winner
])
def test_quote_ok_blends(quote, value, ok):
    assert tx.quote_ok("material", value, quote) is ok


def test_blend_rule_does_not_apply_to_other_keys():
    assert not tx.quote_ok("colour", "clear", "Clear 30% + Black 70%")


# ---- Amendment 4 D2: unit in the label -------------------------------------------------------------

@pytest.mark.parametrize("quote,value,ok", [
    ("Weight (g) 25.5", 25.5, True),
    ("Weight (g) | 25.5", 25.5, True),
    ("Unit weight (gms) | 41.6", 41.6, True),
    ("Weight (grams) 4", 4.0, True),
    ("Net weight (kg) 0.5", 500.0, True),
    ("Weight (oz) 1.5", 42.52, True),
    ("Weight 25.5", 25.5, False),  # no unit anywhere
    ("Weight (mm) 25.5", 25.5, False),
    ("Weight (g) 25.5 mm", 25.5, False),
    ("Weight (g) 25.5 ml", 25.5, False),
    ("Weight (g) 25.5 x 30", 25.5, False),
    ("Weight (g) 25.5 gsm", 25.5, False),
    ("Gauge (g) 25", 25.0, False),
    ("Height (mm) 120 Weight (g) 25.5", 25.5, False),
    ("Weight (g) 25.5 \u00b1 0.5", 25.5, True),
    ("Weight (g) 25.5 +/- 0.5 g", 25.5, True),
    ("Weight (g) 25.5", 30.0, False),  # wrong value
    ("Weight (kg) 25.5", 25.5, False),  # unit converted, so not 25.5 g
    ("25.5", 25.5, False),
    ("Weight (g)", 25.5, False),
])
def test_quote_ok_label_unit(quote, value, ok):
    assert tx.quote_ok("weight_g", value, quote) is ok


def test_label_unit_quote_must_be_on_the_page():
    assert tx.quote_ok("weight_g", 25.5, "Weight (g) | 25.5", "Weight (g)\n25.5")
    assert not tx.quote_ok("weight_g", 25.5, "Weight (g) | 25.5", "Weight (g)\n99")


def test_score_supplement_set_loads_with_empty_predictions(tmp_path):
    truths, preds, texts, messy = score.load_set("supplement", tmp_path)
    assert len(truths) == 12 and messy == set() and all(len(v) >= 1 for v in texts.values())
    r = score.score_set(truths, preds, texts, messy, None, require_cost=False)
    assert r["overall"]["field_accuracy"] < 0.1


def test_s805_whitesolid_alias_only_via_truth_accepted_values():
    t = json.loads((SUPP / "data" / "truth" / "S805.json").read_text())
    col = t["components"][0]["colour"]
    assert col["value"] == "white" and col["accepted_values"] == ["WhiteSolid"]
    assert "WhiteSolid" not in json.dumps(tx.COLOUR_VOCAB)  # not added to the vocabulary
    assert not tx.quote_ok("colour", "white", "WhiteSolid")
    assert tx.quote_ok("colour", "white", "WhiteSolid", extra_words=["WhiteSolid"])
    pages = ["WhiteSolid"]
    mk = lambda q: {"components": [{"name": "cap", "material": {"status": "missing"}, "weight_g": {"status": "missing"},
                                    "colour": {"status": "present", "value": "white", "refs": [{"page": 1, "quote": q}]},
                                    "features": {}}]}
    assert score.score_sheet(t, mk("WhiteSolid"), pages)["untraced"] == 0
    black = mk("WhiteSolid")
    black["components"][0]["colour"]["value"] = "black"
    assert score.score_sheet(t, black, pages)["untraced"] == 1  # the alias does not trace another value
    assert score.score_sheet(t, mk("Colour WhiteSolid W1229"), pages)["untraced"] == 1  # not on the page
