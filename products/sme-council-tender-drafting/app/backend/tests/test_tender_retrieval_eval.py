"""T-206: the Recall@8 retrieval diagnostic (DESIGN 4.2, no bar): the pure scorer, the label-file structure
(eval/keys/retrieval_labels.json, committed and frozen) and the runner on a seeded tenant. No model is called anywhere."""
import json
import re
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

PRODUCT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PRODUCT))

from eval import run as R, score as SC, seed as SD  # noqa: E402

from app.models import Tenant  # noqa: E402
from app.tender import draft as dr  # noqa: E402
from . import tender_files as tf  # noqa: E402
from .conftest import sign_up  # noqa: E402

LABELS = PRODUCT / "eval" / "keys" / "retrieval_labels.json"
PACKS = PRODUCT / "demo-data" / "packs"
SOURCES = PRODUCT / "demo-data" / "pack-sources"


def q(ref, relevant, primary=None, text="t"):
    return {"ref": ref, "text": text, "relevant": relevant, "primary": primary if primary is not None else relevant[:1]}


def lab(*items):
    return {"packs": {"P.docx": list(items)}}


# ---------- retrieval_recall ----------

def test_perfect_recall():
    r = SC.retrieval_recall(lab(q("1", [3, 4])), {"P.docx": {"1": [4, 9, 3]}})
    assert r["pooled"]["recall"] == 1.0 and r["pooled"]["primary_hit_rate"] == 1.0 and r["misses"] == []


def test_partial_recall_and_miss_listed():
    r = SC.retrieval_recall(lab(q("1", [3, 4, 5, 6], [3])), {"P.docx": {"1": [3, 4, 20]}})
    assert r["pooled"]["recall"] == 0.5 and r["pooled"]["primary_hit_rate"] == 1.0
    assert r["misses"] == [{"pack": "P.docx", "ref": "1", "missing": [5, 6], "not_retrieved": False}]


def test_primary_miss_with_recall_above_zero():
    r = SC.retrieval_recall(lab(q("1", [3, 4], [4])), {"P.docx": {"1": [3]}})
    assert r["pooled"]["recall"] == 0.5 and r["pooled"]["primary_hit_rate"] == 0.0


def test_missing_question_counts_zero_and_is_listed():
    r = SC.retrieval_recall(lab(q("1", [3]), q("2", [7])), {"P.docx": {"1": [3]}})
    assert r["pooled"]["recall"] == 0.5 and r["pooled"]["primary_hit_rate"] == 0.5
    assert r["misses"] == [{"pack": "P.docx", "ref": "2", "missing": [7], "not_retrieved": True}]
    assert SC.retrieval_recall(lab(q("1", [3])), {})["pooled"]["recall"] == 0.0


def test_gap_question_is_not_scored_but_counted():
    items = lab(q("1", [3]), {"ref": "2", "text": "t", "relevant": [], "primary": [], "gap": "no evidence"},
                {"ref": "3", "text": "t", "relevant": [], "primary": []})
    r = SC.retrieval_recall(items, {"P.docx": {"1": [3], "2": [1, 2]}})
    assert r["pooled"]["scored"] == 1 and r["pooled"]["recall"] == 1.0
    assert r["pooled"]["gap_questions"] == 2 and r["pooled"]["gap_retrieved_anything"] == 1
    assert r["per_pack"]["P.docx"]["gap_questions"] == 2 and r["misses"] == []


def test_k_cutoff():
    got = {"P.docx": {"1": [1, 2, 3, 4, 5, 6, 7, 8, 9]}}
    assert SC.retrieval_recall(lab(q("1", [9])), got)["pooled"]["recall"] == 0.0          # 9th is outside the top 8
    assert SC.retrieval_recall(lab(q("1", [8])), got)["pooled"]["recall"] == 1.0
    assert SC.retrieval_recall(lab(q("1", [9])), got, k=9)["pooled"]["recall"] == 1.0


def test_all_primaries_hit_rate_needs_every_primary_in_the_top_k():
    items = lab(q("1", [3, 4, 5], [3, 4]), q("2", [6, 7], [6, 7]), q("3", [8], [8]), q("4", [9, 10], [9]))
    got = {"P.docx": {"1": [3, 4], "2": [6, 20], "3": [8], "4": [30]}}
    r = SC.retrieval_recall(items, got)
    # any: q1 yes, q2 yes (6 is in), q3 yes, q4 no; all: q1 yes, q2 no (7 missing), q3 yes, q4 no
    assert r["pooled"]["primary_hit_rate"] == 0.75 and r["pooled"]["all_primaries_hit_rate"] == 0.5
    assert r["per_pack"]["P.docx"]["all_primaries_hit_rate"] == 0.5
    assert SC.retrieval_recall(items, got, k=1)["pooled"]["all_primaries_hit_rate"] == 0.25      # only q3's single primary fits in k=1


def test_all_primaries_is_below_any_primary_on_the_real_labels_when_one_is_dropped():
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    got = {p: {i["ref"]: i["primary"] for i in items} for p, items in labels["packs"].items()}     # perfect retrieval
    assert SC.retrieval_recall(labels, got)["pooled"]["all_primaries_hit_rate"] == 1.0
    half = {p: {i["ref"]: i["primary"][:1] for i in items} for p, items in labels["packs"].items()}
    r = SC.retrieval_recall(labels, half)["pooled"]
    assert r["all_primaries_hit_rate"] < r["primary_hit_rate"] == 1.0                              # some question has 2+ primaries


def test_pooled_is_mean_over_questions_across_packs():
    labels = {"packs": {"A": [q("1", [1])], "B": [q("1", [1, 2]), q("2", [5])]}}
    r = SC.retrieval_recall(labels, {"A": {"1": [1]}, "B": {"1": [1], "2": []}})
    assert r["per_pack"]["A"]["recall"] == 1.0 and r["per_pack"]["B"]["recall"] == 0.25
    assert r["pooled"]["recall"] == pytest.approx((1 + 0.5 + 0) / 3) and r["pooled"]["scored"] == 3


def test_empty_labels_do_not_crash():
    r = SC.retrieval_recall({"packs": {}}, {})
    assert r["pooled"]["recall"] is None and r["misses"] == []


# ---------- the label file (skipped until qa has written it) ----------

def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


@pytest.mark.skipif(not LABELS.is_file(), reason="eval/keys/retrieval_labels.json not written yet")
def test_label_file_structure():
    data = json.loads(LABELS.read_text(encoding="utf-8"))
    demo = json.loads((PACKS / "manifest.json").read_text(encoding="utf-8"))["demo"]
    assert sorted(data["packs"]) == sorted(demo) and len(demo) == 3
    for pack, items in data["packs"].items():
        refs = [i["ref"] for i in items]
        assert items and len(refs) == len(set(refs)), f"{pack}: refs must be unique"
        source = _norm((SOURCES / (Path(pack).stem + ".md")).read_text(encoding="utf-8"))
        for i in items:
            where = f"{pack} {i['ref']}"
            rel, prim = i["relevant"], i.get("primary", [])
            assert all(isinstance(e, int) and 1 <= e <= 32 for e in rel + prim), where
            assert len(rel) == len(set(rel)) and set(prim) <= set(rel), where
            assert sorted(map(str, rel)) == sorted(i.get("why", {})), f"{where}: why keys must equal relevant"
            assert _norm(i["text"]) in source, f"{where}: text not found verbatim in the pack source"


# ---------- the runner on a seeded tenant ----------

def _seeded(app, new_client, tmp_path, files):
    c = new_client()
    sign_up(c, company=SD.FIRM)
    sessions = app.state.db.sessions
    with sessions() as db:
        tenant_id = db.scalar(select(Tenant.id).where(Tenant.name == SD.FIRM))
    ev = tmp_path / "ev"
    ev.mkdir()
    for name, body in files.items():
        (ev / name).write_text(body)
    packs = tmp_path / "packs"
    packs.mkdir()
    (packs / "P1.pdf").write_bytes(tf.pdf([["1. Describe your approach (maximum 300 words)"]]))
    SD.seed(c, sessions, tenant_id, evidence_dir=ev, packs_dir=packs, recorded_dir=tmp_path / "rec")
    return sessions, tenant_id


def test_runner_retrieves_the_right_passage_and_writes_no_model_rows(app, new_client, tmp_path):
    from app.models import AIUsage
    sessions, tenant_id = _seeded(app, new_client, tmp_path, {
        "01-accreditation-summary.md": "# Accreditation\nWe hold ISO 9001 certificate CERT-DEMO-0001 for quality management.\n",
        "02-environmental-policy.md": "# Environment\nWe recycle waste and cut energy use with electric vans.\n"})
    labels = {"packs": {"P.docx": [
        {"ref": "1", "text": "Which ISO 9001 quality certificate do you hold?", "relevant": [1], "primary": [1]},
        {"ref": "2", "text": "How do you recycle waste?", "relevant": [2], "primary": [2]},
        {"ref": "3", "text": "zebra giraffe", "relevant": [], "primary": [], "gap": "nothing"}]}}
    res = R.retrieval_diagnostic(sessions, tenant_id, labels)
    assert res["retrieved"]["P.docx"]["1"][0] == 1 and res["retrieved"]["P.docx"]["2"][0] == 2
    assert res["pooled"]["recall"] == 1.0 and res["pooled"]["gap_retrieved_anything"] == 0 and res["misses"] == []
    assert res["app_passages"] == dr.APP_PASSAGES == 8 and res["at_app_passages"]["recall"] == 1.0
    assert res["pooled"]["all_primaries_hit_rate"] == 1.0 and res["at_app_passages"]["all_primaries_hit_rate"] == 1.0
    assert "labels_sha256" not in res                      # recorded only when the caller (main) passes it
    with sessions() as db:
        assert db.scalar(select(AIUsage.id).limit(1)) is None


def test_runner_on_the_real_library_numbers_passages_like_the_keys(app, new_client, tmp_path):
    sessions, tenant_id = _seeded(app, new_client, tmp_path, {p.name: p.read_text(encoding="utf-8")
                                                             for p in SD.evidence_docs(SD.EVIDENCE_DIR)})
    emap = json.loads((PRODUCT / "eval" / "keys" / "evidence_map.json").read_text(encoding="utf-8"))["entries"][0]
    labels = {"packs": {"P.docx": [{"ref": "1", "text": emap["first80"], "relevant": [emap["e"]], "primary": [emap["e"]]}]}}
    res = R.retrieval_diagnostic(sessions, tenant_id, labels)
    got = res["retrieved"]["P.docx"]["1"]
    assert len(got) <= 8 and len(got) > 5 and all(1 <= n <= 32 for n in got) and emap["e"] in got


def test_the_retrieval_result_records_the_labels_sha256(app, new_client, tmp_path):
    sessions, tenant_id = _seeded(app, new_client, tmp_path, {"01-accreditation-summary.md": "# A\nWe hold ISO 9001 certificate.\n"})
    labels = {"packs": {"P.docx": [{"ref": "1", "text": "ISO 9001 certificate", "relevant": [1], "primary": [1]}]}}
    digest = "ab" * 32
    assert R.retrieval_diagnostic(sessions, tenant_id, labels, labels_sha256=digest)["labels_sha256"] == digest


def test_main_passes_the_sha256_of_the_labels_file_bytes(app, new_client, tmp_path, monkeypatch):
    """main hashes the bytes it read; the value equals sha256sum of the labels file, so a stale results file is detectable."""
    import hashlib
    _seeded(app, new_client, tmp_path, {"01-accreditation-summary.md": "# A\nWe hold ISO 9001 certificate.\n"})
    seen = {}

    def fake(sessions, tenant_id, labels, k=8, labels_sha256=None):
        seen["sha"] = labels_sha256
        return {"labels_sha256": labels_sha256}

    monkeypatch.setattr(R, "retrieval_diagnostic", fake)
    monkeypatch.setattr(R, "RESULTS_DIR", tmp_path / "out")
    monkeypatch.setenv("DATABASE_URL", app.state.db.engine.url.render_as_string(hide_password=False))
    assert R.main(["retrieval"]) == 0
    assert seen["sha"] == hashlib.sha256(LABELS.read_bytes()).hexdigest()
    assert json.loads((tmp_path / "out" / "retrieval.json").read_text())["labels_sha256"] == seen["sha"]


def test_runner_refuses_when_labels_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(R, "KEYS_DIR", tmp_path)
    assert R.main(["retrieval"]) == 4
    assert "retrieval labels not found" in capsys.readouterr().err
