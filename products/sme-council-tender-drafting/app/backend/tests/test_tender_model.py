"""Tender data model: tenant scoping, composite tenant foreign keys, the account export, alembic parity."""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.errors import AppError
from app.models import Tenant
from app.scoped import get_scoped, scoped
from app.tender_export import tender_export
from app.tender_models import (AICache, AITask, Claim, DocumentPage, Draft, EvidenceCounter, EvidenceItem,
                               ExportRecord, Requirement, Signoff, SourceDocument, TenderPack)

from .conftest import sign_up


def _chain(db, tenant_id, tag="x"):
    """One of every object for a tenant; returns {name: row}."""
    pack = TenderPack(tenant_id=tenant_id, title=f"Pack {tag}")
    db.add(pack); db.flush()
    doc = SourceDocument(tenant_id=tenant_id, kind="tender", pack_id=pack.id, filename=f"{tag}.pdf", sha256=tag * 64,
                         mime="application/pdf", page_mode="pdf_page", size_bytes=10)
    db.add(doc); db.flush()
    page = DocumentPage(tenant_id=tenant_id, document_id=doc.id, page_no=1, text=f"page {tag}", char_count=6)
    req = Requirement(tenant_id=tenant_id, pack_id=pack.id, seq=1, kind="question", text=f"Q {tag}",
                      source_document_id=doc.id)
    ev = EvidenceItem(tenant_id=tenant_id, display_no=1, document_id=doc.id, page_from=1, page_to=1,
                      heading="Policy", text=f"quality policy {tag}")
    db.add_all([page, req, ev]); db.flush()
    draft = Draft(tenant_id=tenant_id, requirement_id=req.id, version=1, text=f"draft {tag}", text_sha256="0" * 64,
                  retrieved_ids=[1], cited_ids=[1])
    db.add(draft); db.flush()
    claim = Claim(tenant_id=tenant_id, draft_id=draft.id, seq=1, span="draft", kind="other")
    signoff = Signoff(tenant_id=tenant_id, pack_id=pack.id, reviewer_name="R", statement_version="1",
                      drafts_digest="1" * 64)
    db.add_all([claim, signoff]); db.flush()
    export = ExportRecord(tenant_id=tenant_id, pack_id=pack.id, signoff_id=signoff.id, docx_sha256="2" * 64)
    task = AITask(tenant_id=tenant_id, pack_id=pack.id, kind="extract")
    db.add_all([export, task, EvidenceCounter(tenant_id=tenant_id, next_no=2),
                AICache(tenant_id=tenant_id, key=tag * 64, output_json={"a": 1})])
    db.commit()
    return dict(pack=pack, doc=doc, page=page, req=req, ev=ev, draft=draft, claim=claim, signoff=signoff,
                export=export, task=task)


@pytest.fixture
def two(database):
    db = database.sessions()
    a, b = Tenant(name="Alpha"), Tenant(name="Beta")
    db.add_all([a, b]); db.commit()
    rows_a, rows_b = _chain(db, a.id, "a"), _chain(db, b.id, "b")
    yield db, a, b, rows_a, rows_b
    db.close()


def test_every_new_object_is_404_for_another_tenant(two):
    db, a, b, rows_a, _ = two
    for name, row in rows_a.items():
        model = type(row)
        assert get_scoped(db, model, a.id, row.id) is row
        with pytest.raises(AppError) as err:  # same error as a missing id
            get_scoped(db, model, b.id, row.id)
        with pytest.raises(AppError) as missing:
            get_scoped(db, model, b.id, uuid.uuid4())
        assert (err.value.args, getattr(err.value, "code", None)) == (missing.value.args, getattr(missing.value, "code", None)), name
        assert all(r.tenant_id == b.id for r in db.scalars(scoped(model, b.id)))


@pytest.mark.parametrize("make", [
    lambda t, r: DocumentPage(tenant_id=t, document_id=r["doc"].id, page_no=9),
    lambda t, r: Requirement(tenant_id=t, pack_id=r["pack"].id, seq=2, kind="question", text="x"),
    lambda t, r: Requirement(tenant_id=t, pack_id=uuid.uuid4(), seq=2, kind="question", text="x"),
    lambda t, r: EvidenceItem(tenant_id=t, display_no=7, document_id=r["doc"].id, page_from=1, page_to=1, text="x"),
    lambda t, r: Draft(tenant_id=t, requirement_id=r["req"].id, version=2, text="x", text_sha256="0" * 64),
    lambda t, r: Claim(tenant_id=t, draft_id=r["draft"].id, seq=2, span="s", kind="other"),
    lambda t, r: Signoff(tenant_id=t, pack_id=r["pack"].id, reviewer_name="R", statement_version="1",
                         drafts_digest="1" * 64),
    lambda t, r: ExportRecord(tenant_id=t, pack_id=r["pack"].id, signoff_id=r["signoff"].id, docx_sha256="2" * 64),
    lambda t, r: AITask(tenant_id=t, pack_id=r["pack"].id, kind="draft"),
    lambda t, r: SourceDocument(tenant_id=t, kind="tender", pack_id=r["pack"].id, filename="f", sha256="9" * 64,
                                mime="m", page_mode="pdf_page", size_bytes=1),
])
def test_composite_fk_refuses_a_cross_tenant_child(two, make):
    db, a, b, rows_a, _ = two
    db.add(make(b.id, rows_a))  # tenant B's row pointing at tenant A's parent (or a missing one)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_requirement_document_fk_alone(two):
    """Valid pack (tenant B's own), source document from tenant A: only fk_requirements_document can refuse it."""
    db, a, b, rows_a, rows_b = two
    db.add(Requirement(tenant_id=b.id, pack_id=rows_b["pack"].id, seq=5, kind="question", text="x",
                       source_document_id=rows_a["doc"].id))
    with pytest.raises(IntegrityError) as err:
        db.commit()
    db.rollback()
    assert "fk_requirements_document" in str(err.value)


def test_export_signoff_fk_alone(two):
    """Valid pack (tenant B's own), sign-off from tenant A: only fk_exports_signoff can refuse it."""
    db, a, b, rows_a, rows_b = two
    db.add(ExportRecord(tenant_id=b.id, pack_id=rows_b["pack"].id, signoff_id=rows_a["signoff"].id,
                        docx_sha256="3" * 64))
    with pytest.raises(IntegrityError) as err:
        db.commit()
    db.rollback()
    assert "fk_exports_signoff" in str(err.value)


def test_deleting_a_document_that_requirements_cite_is_refused(two):
    db, a, b, rows_a, rows_b = two
    db.delete(rows_a["doc"])
    with pytest.raises(IntegrityError) as err:
        db.commit()
    db.rollback()
    assert "fk_requirements_document" in str(err.value)
    assert db.get(Requirement, rows_a["req"].id) is not None and db.get(Draft, rows_a["draft"].id) is not None
    # once the requirements are gone the document can go
    db.delete(rows_a["req"]); db.commit()
    db.delete(db.get(SourceDocument, rows_a["doc"].id)); db.commit()
    assert db.get(SourceDocument, rows_a["doc"].id) is None


def test_deleting_the_pack_still_cascades_through_documents_and_requirements(two):
    db, a, b, rows_a, rows_b = two
    db.delete(db.get(TenderPack, rows_a["pack"].id)); db.commit()
    for model in (SourceDocument, Requirement, Draft, Claim):
        assert db.scalars(scoped(model, a.id)).all() == [], model.__name__
    assert db.scalars(scoped(Requirement, b.id)).all()


def test_composite_fk_accepts_the_same_tenant_child(two):
    db, a, _, rows_a, _ = two
    db.add(DocumentPage(tenant_id=a.id, document_id=rows_a["doc"].id, page_no=2))
    db.commit()


def test_duplicate_document_hash_is_refused_per_tenant_only(two):
    db, a, b, _, _ = two
    db.add(SourceDocument(tenant_id=a.id, kind="evidence", filename="dup", sha256="a" * 64, mime="m",
                          page_mode="pdf_page", size_bytes=1))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    # another tenant may store the same file: the hash is unique per tenant, not globally
    db.add(SourceDocument(tenant_id=b.id, kind="evidence", filename="same", sha256="a" * 64, mime="m",
                          page_mode="pdf_page", size_bytes=1))
    db.commit()
    assert db.scalars(scoped(SourceDocument, b.id).where(SourceDocument.sha256 == "a" * 64)).all()


def test_evidence_tsv_is_generated_and_deleting_the_tenant_cascades(two):
    db, a, b, rows_a, _ = two
    db.refresh(rows_a["ev"])
    assert "polici" in rows_a["ev"].tsv
    db.delete(db.get(Tenant, a.id)); db.commit()
    assert db.scalars(scoped(Draft, a.id)).all() == [] and db.scalars(scoped(Draft, b.id)).all()


def test_account_export_covers_the_new_tables_and_only_own_rows(two, new_client):
    db, a, b, rows_a, rows_b = two
    data = tender_export(db, b.id)
    assert set(data) == {"packs", "source_documents", "document_pages", "requirements", "evidence_items", "drafts",
                         "claims", "signoffs", "export_records"}
    assert all(len(v) == 1 for v in data.values())
    assert {r["tenant_id"] for v in data.values() for r in v} == {str(b.id)}
    assert "tsv" not in data["evidence_items"][0]
    # the HTTP export carries the same sections, and is empty for a brand-new tenant
    client = new_client()
    sign_up(client, email="c@gamma.test", company="Gamma")
    exported = client.get("/api/account/export").json()
    assert exported["packs"] == [] and "claims" in exported and "notes" not in exported
