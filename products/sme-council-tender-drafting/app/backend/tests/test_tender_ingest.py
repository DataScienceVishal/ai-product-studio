"""S2: upload limits, sniffing, parse worker refusals, evidence chunking, numbering and retrieval (T-186)."""
import io
import os
import tempfile
import uuid

import pytest
from sqlalchemy import select, text

from app.errors import AppError
from app.models import Tenant
from app.tender import ingest
from app.tender.chunking import chunk_pages
from app.tender.evidence import must_have_tokens, search_evidence
from app.tender.service import ensure_requirement_document
from app.tender_models import (DocumentPage, EvidenceCounter, EvidenceItem, Requirement, SourceDocument, TenderPack)

from . import tender_files as tf
from .conftest import sign_up


@pytest.fixture
def client(new_client):
    c = new_client()
    sign_up(c)
    return c


@pytest.fixture
def db(app):
    s = app.state.db.sessions()
    yield s
    s.close()


def up(client, url, data, name="f.pdf", **form):
    return client.post(url, files={"file": (name, io.BytesIO(data), "application/octet-stream")}, data=form)


def make_pack(client, title="Cleaning tender"):
    r = client.post("/api/packs", json={"title": title})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def tender_url(pid):
    return f"/api/packs/{pid}/documents"


# ---------- limits and sniffing ----------

def test_upload_routes_get_15mb_and_others_keep_1mb(client, settings):
    pid = make_pack(client)
    big = b"%PDF-" + b"x" * (settings.upload_max_bytes + 10)
    r = up(client, tender_url(pid), big)
    assert r.status_code == 413 and r.json()["error"] == "too_large"
    # a 2 MB upload is past the starter's 1 MB cap but under the upload cap: reaches the parser (refused as unreadable, not 413)
    r = up(client, tender_url(pid), b"%PDF-" + b"x" * 2_000_000)
    assert r.status_code == 422 and r.json()["error"] == "parse_failed"
    # other routes still stop at 1 MB
    r = client.post("/api/packs", json={"title": "x", "buyer": "y" * 1_100_000})
    assert r.status_code == 413
    r = up(client, "/api/evidence/documents", b"x" * (settings.upload_max_bytes + 10), "a.txt")
    assert r.status_code == 413


def test_sniff_by_magic_bytes_not_extension(client):
    pid = make_pack(client)
    # a PDF named .docx parses as a PDF; a text file named .pdf is refused for a tender
    pdf = tf.pdf([["Section One Scope"] + tf.wrap(tf.words(80))])
    r = up(client, tender_url(pid), pdf, "tender.docx")
    assert r.status_code == 201 and r.json()["mime"] == "application/pdf"
    r = up(client, tender_url(pid), b"plain text " * 40, "t.pdf")
    assert r.status_code == 415 and r.json()["error"] == "unsupported_tender_type"
    r = up(client, tender_url(pid), b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "t.pdf")
    assert r.status_code == 415 and r.json()["error"] == "unsupported_type"


def test_txt_accepted_for_evidence_only_and_strict(client):
    body = ("Quality Policy\n\n" + tf.words(150) + "\n\nEnvironment\n\n" + tf.words(150)).encode()
    r = up(client, "/api/evidence/documents", body, "policy.txt", category="policy")
    assert r.status_code == 201, r.text
    assert r.json()["page_mode"] == "text_block" and r.json()["passages"] >= 1
    r = up(client, "/api/evidence/documents", b"caf\xe9 " * 100, "latin.txt")  # not UTF-8
    assert r.status_code == 415 and r.json()["error"] == "unsupported_type"
    r = up(client, "/api/evidence/documents", b"abc\x00def " * 50, "nul.txt")
    assert r.status_code == 415
    r = up(client, "/api/evidence/documents", body, "p.txt", category="nonsense")
    assert r.status_code == 422


def test_filename_is_sanitised(client):
    r = up(client, "/api/evidence/documents", ("Policy words here. " * 20).encode(), "../../etc/pa\x01ss.txt")
    assert r.status_code == 201 and r.json()["filename"] == "pass.txt"
    assert "/" not in r.json()["filename"] and ".." not in r.json()["filename"]


# ---------- refusals ----------

@pytest.mark.parametrize("make,code,status", [
    (lambda: tf.encrypted_pdf(), "encrypted", 422),
    (lambda: tf.OLE_BYTES, "encrypted", 422),
    (lambda: tf.docm_bytes(), "macro_file", 422),
    (lambda: tf.zip_bomb_bytes(), "zip_bomb", 422),
    (lambda: tf.many_entries_bytes(), "zip_bomb", 422),
    (lambda: tf.xxe_docx(), "xml_entities", 422),
    (lambda: tf.image_only_pdf(), "image_only", 422),
    (lambda: b"%PDF-1.4\nthis is not a real pdf", "parse_failed", 422),
    (lambda: b"PK\x03\x04 not really a zip", "unsupported_type", 415),
])
def test_refusals_for_tender_and_evidence(client, make, code, status):
    data = make()
    pid = make_pack(client)
    for url, form in ((tender_url(pid), {}), ("/api/evidence/documents", {"category": "policy"})):
        r = up(client, url, data, "bad.bin", **form)
        assert r.status_code == status and r.json()["error"] == code, (url, r.text)
    assert client.get("/livez").status_code == 200  # server still up
    assert client.get("/api/evidence/documents").json()["documents"] == []  # nothing stored


def test_tender_with_one_image_only_page_refused_but_not_evidence(client):
    data = tf.pdf([["Scope " + w for w in tf.wrap(tf.words(60), 60)], ["x"]])  # page 2 has under 30 characters
    pid = make_pack(client)
    r = up(client, tender_url(pid), data)
    assert r.status_code == 422 and r.json()["error"] == "image_only"
    r = up(client, "/api/evidence/documents", data, category="policy")
    assert r.status_code == 201


def test_page_cap_per_file(client):
    data = tf.pdf([[f"Page {i} " + "word " * 20] for i in range(61)])
    r = up(client, tender_url(make_pack(client)), data)
    assert r.status_code == 422 and r.json()["error"] == "too_many_pages"


def test_xxe_entity_is_not_expanded_by_python_docx_parser():
    from docx.oxml import parse_xml
    el = parse_xml(b'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY x SYSTEM "file:///etc/hostname">]>'
                   b'<w:t xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">a&x;b</w:t>')
    host = open("/etc/hostname").read().strip() if os.path.exists("/etc/hostname") else "\0none"
    assert host not in (el.text or "")


def test_worker_gets_empty_environment_and_temp_file_removed(monkeypatch):
    seen = {}
    real = ingest.subprocess.run

    def spy(cmd, **kw):
        seen["env"], seen["cmd"] = kw["env"], cmd
        seen["tmp"] = os.path.dirname(cmd[3])
        return real(cmd, **kw)
    monkeypatch.setattr(ingest.subprocess, "run", spy)
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    parsed = ingest.parse_upload(tf.pdf([["Hello tender world, this page has enough text to count."]]),
                                 allow_text=False, max_pages=60)
    assert seen["env"] == {} and seen["cmd"][1] == "-I" and os.path.isabs(seen["cmd"][2])
    assert not os.path.exists(seen["tmp"])
    assert parsed.pages[0]["text"].startswith("Hello tender world")


def test_worker_timeout_is_parse_failed_not_500(monkeypatch):
    def boom(*a, **k):
        raise ingest.subprocess.TimeoutExpired("x", 1)
    monkeypatch.setattr(ingest.subprocess, "run", boom)
    with pytest.raises(ingest.Refused) as e:
        ingest.parse_upload(tf.pdf([["Hello tender world, this page has enough text to count."]]), allow_text=False, max_pages=60)
    assert e.value.code == "parse_failed"


# ---------- documents, pages ----------

def test_pdf_pages_are_numbered_and_stored(client, db):
    pid = make_pack(client)
    data = tf.pdf([[f"Page {n} unique marker{n} " + "alpha beta gamma delta " * 3] for n in (1, 2, 3)])
    r = up(client, tender_url(pid), data, "Tender.pdf")
    assert r.status_code == 201 and r.json()["page_count"] == 3 and r.json()["page_mode"] == "pdf_page"
    pages = db.scalars(select(DocumentPage).order_by(DocumentPage.page_no)).all()
    assert [p.page_no for p in pages] == [1, 2, 3]
    assert all(f"marker{p.page_no}" in p.text and not p.image_only for p in pages)
    doc = db.scalar(select(SourceDocument))
    assert doc.created_by is not None and doc.size_bytes == len(data) and len(doc.sha256) == 64


def test_docx_with_page_breaks_and_without(client, db):
    pid = make_pack(client)
    paras = [("Section A", "Heading 1"), (tf.words(40, "alpha"), None), ("Section B", "Heading 1"), (tf.words(40, "beta"), None)]
    r = up(client, tender_url(pid), tf.docx_bytes(paras, page_break_after={1}), "a.docx")
    assert r.status_code == 201 and r.json()["page_mode"] == "docx_break" and r.json()["page_count"] == 2
    r = up(client, tender_url(pid), tf.docx_bytes(paras + [("extra", None)]), "b.docx")
    assert r.status_code == 201 and r.json()["page_mode"] == "docx_block" and r.json()["page_count"] == 1


def test_duplicate_sha_refused_per_tenant_but_not_across(client, new_client):
    data = tf.pdf([["A policy page with enough words to count as text. " * 2]])
    assert up(client, "/api/evidence/documents", data, category="policy").status_code == 201
    r = up(client, "/api/evidence/documents", data, category="policy")
    assert r.status_code == 409 and r.json()["error"] == "duplicate_document"
    other = new_client(); sign_up(other, email="b@other.test", company="Other")
    assert up(other, "/api/evidence/documents", data, category="policy").status_code == 201


def test_pack_size_and_rate_and_pages_per_day_limits(new_client, app, settings):
    app.state.settings.upload_max_pack_bytes = 3000
    c = new_client(); sign_up(c)
    pid = make_pack(c)
    d1 = tf.pdf([["First tender document with plenty of selectable text. " * 3]])
    assert up(c, tender_url(pid), d1).status_code == 201
    d2 = tf.pdf([["Second tender document with plenty of selectable text. " * 3]]) + b"\n%" + b"x" * 3000
    r = up(c, tender_url(pid), d2)
    assert r.status_code == 413 and r.json()["error"] == "pack_too_large"
    app.state.settings.upload_max_pack_bytes = 10**8
    app.state.settings.upload_pages_per_day = 2
    d3 = tf.pdf([["Third doc " * 8], ["page two text " * 8]])
    r = up(c, tender_url(pid), d3)
    assert r.status_code == 429 and r.json()["error"] == "page_limit"
    app.state.settings.upload_pages_per_day = 1000
    app.state.settings.uploads_per_hour = 2
    r = up(c, tender_url(pid), tf.pdf([["Fourth doc " * 9]]))  # second upload this hour (first was d1, d2 and d3 counted too)
    assert r.status_code == 429 and r.json()["error"] == "rate_limited"


# ---------- chunking and numbering ----------

def test_chunking_sizes_headings_and_pages():
    pages = [{"text": "Quality Policy\n" + "\n\n".join(tf.words(100, f"q{i}") for i in range(3)), "headings": []},
             {"text": "Environmental Policy\n" + tf.words(150), "headings": []}]
    ps = chunk_pages(pages)
    assert ps and all(len(p.text.split()) <= 410 for p in ps)
    assert ps[0].heading == "Quality Policy" and ps[0].page_from == 1
    assert ps[-1].heading == "Environmental Policy" and ps[-1].page_from == ps[-1].page_to == 2
    assert not any("Quality Policy" in p.text for p in ps if p.page_from == 2)
    big = chunk_pages([{"text": tf.words(1000), "headings": []}])
    assert len(big) >= 3 and all(len(p.text.split()) <= 400 for p in big)


def test_evidence_numbers_per_tenant_never_reused(client, new_client, db):
    d = lambda n: ("Heading One\n\n" + tf.words(150, f"doc{n}")).encode()
    r1 = up(client, "/api/evidence/documents", d(1), "a.txt")
    r2 = up(client, "/api/evidence/documents", d(2), "b.txt")
    assert r1.status_code == r2.status_code == 201
    nums = [n for (n,) in db.execute(select(EvidenceItem.display_no).order_by(EvidenceItem.display_no))]
    assert nums == list(range(1, len(nums) + 1)) and len(nums) >= 2
    first_doc = client.get("/api/evidence/documents").json()["documents"][0]["id"]
    assert client.delete(f"/api/documents/{first_doc}").status_code == 204
    r3 = up(client, "/api/evidence/documents", d(3), "c.txt")
    assert r3.status_code == 201
    db.expire_all()
    after = [n for (n,) in db.execute(select(EvidenceItem.display_no).order_by(EvidenceItem.display_no))]
    assert min(after) > 1 and max(after) > max(nums)  # numbers of the deleted document are not handed out again
    other = new_client(); sign_up(other, email="o@o.test", company="O")
    up(other, "/api/evidence/documents", d(9), "z.txt")
    db.expire_all()
    other_tenant = db.scalar(select(Tenant.id).where(Tenant.name == "O"))
    assert min(n for (n,) in db.execute(select(EvidenceItem.display_no).where(EvidenceItem.tenant_id == other_tenant))) == 1


def test_failed_upload_gives_numbers_back(client, db, monkeypatch):
    from app.routes import tender
    monkeypatch.setattr(tender, "chunk_pages", lambda pages: (_ for _ in ()).throw(RuntimeError("boom")))
    r = up(client, "/api/evidence/documents", ("Heading\n\n" + tf.words(150)).encode(), "a.txt")
    assert r.status_code == 500
    assert db.scalar(select(EvidenceCounter.next_no)) is None


# ---------- retrieval ----------

ISO9001 = "ISO 9001 Quality Management\n\n" + tf.words(130, "Our quality management system is certified to ISO 9001 and audited annually by an accredited body.")
ISO14001 = "ISO 14001 Environmental Management\n\n" + tf.words(130, "Our environmental management system is certified to ISO 14001 and covers waste, energy and emissions.")


def seed_iso(client):
    assert up(client, "/api/evidence/documents", ISO9001.encode(), "q.txt", category="accreditation").status_code == 201
    assert up(client, "/api/evidence/documents", ISO14001.encode(), "e.txt", category="accreditation").status_code == 201


def test_iso_14001_ranks_over_iso_9001(client):
    seed_iso(client)
    r = client.get("/api/evidence/search", params={"q": "Do you hold ISO 14001 accreditation?"})
    res = r.json()["results"]
    assert r.status_code == 200 and len(res) == 2  # OR query: the ISO 9001 passage still matches on "iso"
    assert "ISO 14001" in res[0]["text"] and res[0]["document"] == "e.txt" and res[0]["label"].startswith("E-")
    assert res[0]["score"] > res[1]["score"] + 0.5
    # a plain-word question still finds both and puts the quality passage first for a quality question
    res = client.get("/api/evidence/search", params={"q": "quality management system audited"}).json()["results"]
    assert "ISO 9001" in res[0]["text"]


def test_must_have_tokens():
    pats = [p.pattern for p, _ in must_have_tokens("Hold ISO14001, CHAS, Cyber Essentials and a 2023 audit? GDPR")]
    assert len(pats) >= 5
    assert any(p.search("we hold ISO 14001") for p, _ in must_have_tokens("ISO14001"))


def test_top_8_with_at_most_3_per_document(client, db):
    for i in range(3):
        body = "\n\n".join(f"Safety Heading {i}{j}\n\n" + tf.words(125, f"scaffold safety training record{i}{j}") for j in range(5))
        assert up(client, "/api/evidence/documents", body.encode(), f"d{i}.txt").status_code == 201
    tid = db.scalar(select(Tenant.id))
    hits = search_evidence(db, tid, "scaffold safety training")
    assert len(hits) == 8
    from collections import Counter
    assert max(Counter(h.document_id for h in hits).values()) == 3


def test_no_cross_tenant_retrieval(client, new_client, db):
    seed_iso(client)
    other = new_client(); sign_up(other, email="b@b.test", company="B")
    assert other.get("/api/evidence/search", params={"q": "ISO 14001 environmental"}).json()["results"] == []
    # identical evidence in both tenants: each sees only its own E-numbers and documents
    seed_iso(other)
    mine = {r["id"] for r in client.get("/api/evidence/search", params={"q": "ISO 14001"}).json()["results"]}
    theirs = {r["id"] for r in other.get("/api/evidence/search", params={"q": "ISO 14001"}).json()["results"]}
    assert mine and theirs and not (mine & theirs)
    # the SQL itself carries the tenant: the function with tenant B's id returns none of A's rows
    ids = {str(i) for (i,) in db.execute(text("SELECT id FROM evidence_items"))}
    a = db.scalar(select(Tenant.id).where(Tenant.name == "Acme Ltd"))
    assert {str(h.id) for h in search_evidence(db, a, "ISO 14001")} == mine and mine <= ids


def test_deleted_documents_and_empty_queries_return_nothing(client, db):
    seed_iso(client)
    tid = db.scalar(select(Tenant.id))
    assert search_evidence(db, tid, "the of and") == [] and search_evidence(db, tid, "") == []
    for d in client.get("/api/evidence/documents").json()["documents"]:
        client.delete(f"/api/documents/{d['id']}")
    assert client.get("/api/evidence/search", params={"q": "ISO 14001"}).json()["results"] == []


def test_search_needs_sign_in(new_client):
    assert new_client().get("/api/evidence/search", params={"q": "x"}).status_code == 401


# ---------- T-197 leftovers ----------

def _req(db, tenant_id, pack_id, doc_id):
    r = Requirement(tenant_id=tenant_id, pack_id=pack_id, seq=1, kind="question", text="Q", source_document_id=doc_id)
    db.add(r); db.commit()
    return r


def test_delete_document_cited_by_requirement_is_409_then_works(client, db):
    pid = make_pack(client)
    doc = up(client, tender_url(pid), tf.pdf([["Tender questions text that is long enough. " * 3]])).json()
    tid = db.scalar(select(Tenant.id))
    req = _req(db, tid, uuid.UUID(pid), uuid.UUID(doc["id"]))
    r = client.delete(f"/api/documents/{doc['id']}")
    assert r.status_code == 409 and r.json()["error"] == "document_in_use"
    assert "requirements" in r.json()["message"].lower()
    assert client.get(f"/api/packs/{pid}/documents").json()["documents"][0]["id"] == doc["id"]
    db.delete(req); db.commit()
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 204


def test_pack_delete_cascades_but_cross_pack_citation_gives_409(client, db):
    p1, p2 = make_pack(client, "One"), make_pack(client, "Two")
    d1 = up(client, tender_url(p1), tf.pdf([["Tender pack one text that is long enough. " * 3]])).json()
    tid = db.scalar(select(Tenant.id))
    own = up(client, tender_url(p2), tf.pdf([["Tender pack two text that is long enough. " * 3]])).json()
    _req(db, tid, uuid.UUID(p2), uuid.UUID(own["id"]))
    assert client.delete(f"/api/packs/{p2}").status_code == 204  # own requirements go with the pack
    _req(db, tid, uuid.UUID(p1), uuid.UUID(d1["id"]))
    p3 = make_pack(client, "Three")
    db.add(Requirement(tenant_id=tid, pack_id=uuid.UUID(p3), seq=1, kind="question", text="X",
                       source_document_id=uuid.UUID(d1["id"]))); db.commit()  # schema allows a cross-pack cite
    r = client.delete(f"/api/packs/{p1}")
    assert r.status_code == 409 and r.json()["error"] == "document_in_use"


def test_delete_other_tenants_document_is_404(client, new_client):
    doc = up(client, "/api/evidence/documents", ("Policy text " * 30).encode(), "a.txt").json()
    other = new_client(); sign_up(other, email="x@x.test", company="X")
    assert other.delete(f"/api/documents/{doc['id']}").status_code == 404
    assert other.delete(f"/api/packs/{uuid.uuid4()}").status_code == 404


def test_requirement_must_cite_a_document_of_its_own_pack(client, db):
    p1, p2 = make_pack(client, "One"), make_pack(client, "Two")
    d1 = uuid.UUID(up(client, tender_url(p1), tf.pdf([["Tender pack one text that is long enough. " * 3]])).json()["id"])
    ev = uuid.UUID(up(client, "/api/evidence/documents", ("Policy text " * 30).encode(), "a.txt").json()["id"])
    tid = db.scalar(select(Tenant.id))
    assert ensure_requirement_document(db, tid, uuid.UUID(p1), d1).id == d1
    assert ensure_requirement_document(db, tid, uuid.UUID(p1), None) is None
    for pack, doc in ((p2, d1), (p1, ev), (p1, uuid.uuid4())):
        with pytest.raises(AppError) as e:
            ensure_requirement_document(db, tid, uuid.UUID(pack), doc)
        assert e.value.status == 422 and e.value.code == "document_not_in_pack"
