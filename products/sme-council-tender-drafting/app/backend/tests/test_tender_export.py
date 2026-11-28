"""S8: Word export and reopen (T-192). No model calls: ScriptedFakeAI and the Judge fake."""
from __future__ import annotations

import io
import zipfile

from docx import Document
from sqlalchemy import select

import inspect

from app.tender import claimcheck, export, gate
from app.tender_models import Claim, Draft, EvidenceItem, ExportRecord, Signoff, TenderPack

from .conftest import sign_up
from .test_tender_claimcheck import Judge, check_now, client, db, evidence_doc, honest, pack_status  # noqa: F401
from .test_tender_draft import latest
from .test_tender_review import SIGN, ready_pack


def docx_text(resp) -> tuple[str, str, str]:
    doc = Document(io.BytesIO(resp.content))
    body = "\n".join(p.text for p in doc.paragraphs)
    return body, doc.sections[0].header.paragraphs[0].text, doc.sections[0].footer.paragraphs[0].text


def signed_pack(client, app):
    pid, rid = ready_pack(client, app)
    assert client.post(f"/api/packs/{pid}/signoff", json=SIGN).status_code == 201
    return pid, rid


def test_export_docx_matches_the_database(client, app, db):
    pid, rid = signed_pack(client, app)
    r = client.get(f"/api/packs/{pid}/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert r.headers["content-disposition"].startswith("attachment; filename=\"") and r.headers["content-disposition"].endswith(".docx\"")
    body, header, footer = docx_text(r)
    d = db.scalar(select(Draft).order_by(Draft.version.desc()))
    for para in d.text.split("\n"):
        if para.strip():
            assert para in body
    assert d.cited_ids and all(f"[E-{n}]" in body for n in d.cited_ids)
    assert "Appendix: claims and their sources" in body
    so0 = db.scalar(select(Signoff))
    assert header == f"Draft prepared with AI assistance; reviewed by Ann Lee on {so0.signed_at:%d %B %Y}"
    doc = Document(io.BytesIO(r.content))
    table = doc.tables[0]
    assert [c.text for c in table.rows[0].cells] == ["Claim", "Evidence", "Document", "Page", "Supporting quote"]
    latest_ids = {d.id for d in db.scalars(select(Draft)) if d.version == max(
        x.version for x in db.scalars(select(Draft)) if x.requirement_id == d.requirement_id)}
    claims = db.scalars(select(Claim).where(Claim.draft_id.in_(latest_ids)).order_by(Claim.seq)).all()
    assert claims and len(table.rows) == 1 + len(claims)
    for row, c in zip(table.rows[1:], claims):
        cells = [x.text for x in row.cells]
        assert c.span in cells[0] and cells[4] == (c.evidence_quote or "")
        assert cells[1] == (", ".join(f"[E-{n}]" for n in sorted(set(c.cited_ids))) or "no citation")
        if c.cited_ids:
            assert cells[2] == "quality.txt" and cells[3] == "1"
    assert footer == gate.STATEMENT_TEXT
    rec = db.scalar(select(ExportRecord))
    so = db.scalar(select(Signoff))
    assert rec.signoff_id == so.id and len(rec.docx_sha256) == 64 and rec.created_by is not None


def test_export_is_deterministic(client, app):
    pid, _ = signed_pack(client, app)
    a = client.get(f"/api/packs/{pid}/export").content
    b = client.get(f"/api/packs/{pid}/export").content
    assert a == b
    assert zipfile.ZipFile(io.BytesIO(a)).testzip() is None


def test_export_refused_without_sign_off(client, app, db):
    pid, _ = ready_pack(client, app)
    r = client.get(f"/api/packs/{pid}/export")
    assert r.status_code == 409 and r.json()["error"] == "export_blocked" and "no_signoff" in r.json()["message"]
    assert db.scalar(select(ExportRecord)) is None


def test_export_refused_after_evidence_soft_delete(client, app, db):
    pid, _ = signed_pack(client, app)
    client.delete(f"/api/documents/{evidence_doc(client)[0]['id']}")
    r = client.get(f"/api/packs/{pid}/export")
    assert r.status_code == 409 and "evidence_removed" in r.json()["message"]
    assert db.scalar(select(ExportRecord)) is None


def test_export_refused_when_the_signed_answers_changed_underneath(client, app, db):
    pid, rid = signed_pack(client, app)
    db.execute(Draft.__table__.update().values(text="Something else entirely."))
    db.commit()
    r = client.get(f"/api/packs/{pid}/export")
    assert r.status_code == 409 and r.json()["error"] == "export_blocked"


def test_reopen_voids_the_sign_off_and_export_is_refused(client, app, db):
    pid, rid = signed_pack(client, app)
    r = client.post(f"/api/packs/{pid}/reopen")
    assert r.status_code == 200 and r.json()["pack"]["status"] == "ready"
    so = db.scalar(select(Signoff))
    assert so.voided_at is not None  # kept for audit
    g = client.get(f"/api/packs/{pid}/export")
    assert g.status_code == 409 and "no_signoff" in g.json()["message"]
    assert client.get(f"/api/packs/{pid}/coverage").json()["signoff"] is None
    assert client.post(f"/api/packs/{pid}/reopen").status_code == 409  # not signed any more


def test_reopen_needs_a_signed_pack(client, app):
    pid, _ = ready_pack(client, app)
    r = client.post(f"/api/packs/{pid}/reopen")
    assert r.status_code == 409 and r.json()["error"] == "not_signed"


def test_reopen_edit_sign_again_export(client, app, db):
    pid, rid = signed_pack(client, app)
    first = client.get(f"/api/packs/{pid}/export")
    assert client.post(f"/api/packs/{pid}/reopen").status_code == 200
    old = latest(client, rid)["draft"]["text"]
    new = old + "\n\n" + old.split("\n")[0]  # a changed answer whose sentences are still verbatim from the cited passage
    assert client.put(f"/api/requirements/{rid}/draft", json={"text": new}).status_code == 201
    assert pack_status(client, pid) == "drafting"
    assert client.get(f"/api/packs/{pid}/export").status_code == 409
    check_now(client, app, pid, Judge(honest))
    assert pack_status(client, pid) == "ready"
    assert client.post(f"/api/packs/{pid}/signoff", json=SIGN | {"reviewer_name": "Bo Chen"}).status_code == 201
    r = client.get(f"/api/packs/{pid}/export")
    assert r.status_code == 200
    body, header, _ = docx_text(r)
    assert "Bo Chen" in header and new.split("\n")[0] in body
    assert r.content != first.content
    assert len(db.scalars(select(ExportRecord)).all()) == 2
    assert len(db.scalars(select(Signoff)).all()) == 2


def test_cross_tenant_export_and_reopen_are_404(client, app, new_client, db):
    pid, _ = signed_pack(client, app)
    other = new_client()
    sign_up(other, email="o9@o.test", company="O9")
    assert other.get(f"/api/packs/{pid}/export").status_code == 404
    assert other.post(f"/api/packs/{pid}/reopen").status_code == 404
    assert db.scalar(select(ExportRecord)) is None and pack_status(client, pid) == "signed"


def test_export_and_reopen_need_a_session(client, app, new_client):
    pid, _ = signed_pack(client, app)
    anon = new_client()
    assert anon.get(f"/api/packs/{pid}/export").status_code == 401
    assert anon.post(f"/api/packs/{pid}/reopen").status_code == 401


def test_signoff_takes_the_pack_row_lock(client, app):
    """T-199: a sign-off waits for a holder of the pack row, so an edit cannot slip in between check and sign-off."""
    import threading
    import time
    pid, _ = ready_pack(client, app)
    holder = app.state.db.sessions()
    holder.execute(select(TenderPack).where(TenderPack.id == pid).with_for_update()).scalar_one()
    out = {}
    t = threading.Thread(target=lambda: out.update(r=client.post(f"/api/packs/{pid}/signoff", json=SIGN)))
    t.start()
    time.sleep(1.0)
    assert t.is_alive()
    holder.rollback()
    holder.close()
    t.join(15)
    assert out["r"].status_code == 201


def test_one_loader_feeds_export_signoff_and_claimcheck(client, app, db):
    pid, _ = signed_pack(client, app)
    tid = db.scalar(select(TenderPack.tenant_id))
    assert claimcheck.load_gate_inputs(db, tid, pid) == export.gate_inputs(export.load_rows(db, tid, pid))
    assert "load_rows" in inspect.getsource(claimcheck.load_gate_inputs)  # no second copy of the queries to drift


def test_export_loads_only_the_cited_evidence_rows(client, app, db):
    pid, _ = signed_pack(client, app)
    tid = db.scalar(select(TenderPack.tenant_id))
    first = db.scalar(select(EvidenceItem))
    db.add(EvidenceItem(tenant_id=tid, display_no=900, document_id=first.document_id, page_from=1, page_to=1,
                        heading="other", text="uncited " * 50))
    db.commit()
    rows = export.load_rows(db, tid, pid)
    cited = {n for c in rows.claims for n in c.cited_ids}
    assert cited and set(rows.evidence) == cited and 900 in rows.live and 900 not in rows.evidence
    assert client.get(f"/api/packs/{pid}/export").status_code == 200  # the extra live row does not disturb the gate


def test_export_moves_the_pack_to_exported_and_stays_downloadable(client, app, db):
    pid, _ = signed_pack(client, app)
    assert client.get(f"/api/packs/{pid}/export").status_code == 200
    assert pack_status(client, pid) == "exported"
    assert client.get(f"/api/packs/{pid}/export").status_code == 200  # re-download
    assert len(db.scalars(select(ExportRecord)).all()) == 2
    assert client.get(f"/api/packs/{pid}/coverage").json()["signoff"] is not None
    assert client.post(f"/api/packs/{pid}/signoff", json=SIGN).status_code == 409
    r = client.post(f"/api/packs/{pid}/reopen")
    assert r.status_code == 200 and r.json()["pack"]["status"] == "ready"


def test_reopen_does_not_say_ready_when_evidence_was_removed(client, app, db):
    pid, _ = signed_pack(client, app)
    client.delete(f"/api/documents/{evidence_doc(client)[0]['id']}")
    r = client.post(f"/api/packs/{pid}/reopen")
    assert r.status_code == 200 and r.json()["pack"]["status"] == "drafting"
