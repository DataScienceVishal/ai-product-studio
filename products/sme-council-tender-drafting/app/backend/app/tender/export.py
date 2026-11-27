"""Word export (DESIGN 4.5). The rows are read once, the pure gate runs on plain values built from those same objects, and
the document is rendered from them too, so what was checked is what is written. No AI, no network, no fields or hyperlinks.
The output is deterministic for the same rows (fixed core properties and zip timestamps)."""
from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone

from docx import Document
from docx.shared import Pt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Tenant
from ..tender_models import Claim, Draft, EvidenceItem, Requirement, Signoff, SourceDocument, TenderPack
from . import gate

_CITE = re.compile(r"\[E-(\d+)\]")
_XML_BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿\ud800-\udfff]")
_FIXED = datetime(2000, 1, 1, tzinfo=timezone.utc)
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ExportRefused(Exception):
    def __init__(self, reasons: list[str]):
        super().__init__("; ".join(reasons))
        self.reasons = reasons


@dataclass
class Rows:
    pack: TenderPack
    tenant_name: str
    requirements: list[Requirement]
    drafts: list[Draft]
    claims: list[Claim]
    signoff: Signoff | None
    evidence: dict[int, tuple[EvidenceItem, str]]  # live evidence by display number -> (item, document name)


def clean(text: str) -> str:
    return _XML_BAD.sub("", text or "")


def safe_filename(title: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-")[:60] or "tender-pack"
    return f"{stem}-draft.docx"


def load_rows(db: Session, tenant_id, pack_id) -> Rows:
    pack = db.scalar(select(TenderPack).where(TenderPack.tenant_id == tenant_id, TenderPack.id == pack_id))
    tenant = db.get(Tenant, tenant_id)
    reqs = list(db.scalars(select(Requirement).where(Requirement.tenant_id == tenant_id, Requirement.pack_id == pack_id)
                           .order_by(Requirement.seq)))
    drafts = list(db.scalars(select(Draft).where(Draft.tenant_id == tenant_id, Draft.requirement_id.in_([r.id for r in reqs]))))
    claims = list(db.scalars(select(Claim).where(Claim.tenant_id == tenant_id, Claim.draft_id.in_([d.id for d in drafts]))
                             .order_by(Claim.draft_id, Claim.seq)))
    so = db.scalar(select(Signoff).where(Signoff.tenant_id == tenant_id, Signoff.pack_id == pack_id, Signoff.voided_at.is_(None))
                   .order_by(Signoff.signed_at.desc()).limit(1))
    ev = {e.display_no: (e, name) for e, name in db.execute(
        select(EvidenceItem, SourceDocument.filename).join(
            SourceDocument, (SourceDocument.tenant_id == EvidenceItem.tenant_id) & (SourceDocument.id == EvidenceItem.document_id))
        .where(EvidenceItem.tenant_id == tenant_id, EvidenceItem.deleted_at.is_(None), SourceDocument.deleted_at.is_(None)))}
    return Rows(pack, tenant.name if tenant else "", reqs, drafts, claims, so, ev)


def gate_inputs(rows: Rows):
    reqs = [gate.GateReq(str(r.id), r.kind, r.status, r.word_limit) for r in rows.requirements]
    drafts = [gate.GateDraft(str(d.id), str(d.requirement_id), d.version, d.text, d.text_sha256, d.check_sha256) for d in rows.drafts]
    claims = [gate.GateClaim(str(c.draft_id), c.verdict, tuple(c.cited_ids)) for c in rows.claims]
    so = gate.GateSignoff(rows.signoff.statement_version, rows.signoff.drafts_digest) if rows.signoff else None
    return gate.GatePack(rows.pack.status), reqs, drafts, claims, so, set(rows.evidence)


def _fix_zip(data: bytes) -> bytes:
    """python-docx stamps zip entries with the clock; rewrite them with a fixed time so the same rows give the same bytes."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zi = zipfile.ZipInfo(info.filename, date_time=(2000, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            zout.writestr(zi, zin.read(info.filename))
    return out.getvalue()


def render(rows: Rows) -> bytes:
    so = rows.signoff
    assert so is not None
    doc = Document()
    cp = doc.core_properties
    cp.author = cp.last_modified_by = "Tender drafting assistant"
    cp.title = clean(rows.pack.title)
    cp.created = cp.modified = _FIXED
    cp.revision = 1
    sec = doc.sections[0]
    sec.header.paragraphs[0].text = clean(
        f"Draft produced with AI assistance; reviewed and signed off by {so.reviewer_name} on {so.signed_at:%d %B %Y}")
    sec.footer.paragraphs[0].text = clean(gate.STATEMENT_TEXT)
    doc.add_heading(clean(rows.pack.title), 0)
    meta = [clean(rows.tenant_name)]
    if rows.pack.buyer:
        meta.append(f"Buyer: {clean(rows.pack.buyer)}")
    doc.add_paragraph(" | ".join(meta))
    doc.add_paragraph("Remove the [E-n] markers and any gap markers before submission.").runs[0].italic = True

    latest = gate.latest_drafts(gate.GateDraft(str(d.id), str(d.requirement_id), d.version, d.text, d.text_sha256, d.check_sha256)
                                for d in rows.drafts)
    cited: set[int] = set()
    for r in sorted((r for r in rows.requirements if r.status == "confirmed" and r.kind == "question"), key=lambda r: r.seq):
        d = latest[str(r.id)]
        head = f"{r.ref}  " if r.ref else ""
        doc.add_heading(clean(f"{head}{r.text}"[:300]), 1)
        words = gate.count_words(d.text)
        doc.add_paragraph(f"Word limit: {r.word_limit}; words: {words}" if r.word_limit else f"Words: {words}").runs[0].font.size = Pt(9)
        for para in clean(d.text).split("\n"):
            if para.strip():
                doc.add_paragraph(para)
        cited |= {int(n) for n in _CITE.findall(d.text)}
    doc.add_heading("Appendix: evidence cited", 1)
    if not cited:
        doc.add_paragraph("No evidence is cited.")
    for n in sorted(cited):
        item, name = rows.evidence[n]  # a missing one would have blocked the gate; KeyError here is a refusal, not a silent gap
        pages = str(item.page_from) if item.page_from == item.page_to else f"{item.page_from}-{item.page_to}"
        p = doc.add_paragraph()
        p.add_run(f"[E-{n}] ").bold = True
        p.add_run(clean(f"{name}, page {pages}"))
        doc.add_paragraph(clean(" ".join(item.text.split())))
    buf = io.BytesIO()
    doc.save(buf)
    return _fix_zip(buf.getvalue())


def build(db: Session, tenant_id, pack_id) -> tuple[bytes, Rows]:
    """Load once, gate, render from the same objects. Raises ExportRefused with the gate's reasons."""
    rows = load_rows(db, tenant_id, pack_id)
    allowed, reasons = gate.export_allowed(*gate_inputs(rows), gate.STATEMENT_VERSION)
    if rows.pack.status not in ("signed", "exported"):
        reasons = [*reasons, f"not_signed: the pack is '{rows.pack.status}', not signed off"]
    if reasons or not allowed or rows.signoff is None:
        raise ExportRefused(reasons or ["no_signoff: the pack has not been signed off"])
    data = render(rows)
    return data, rows


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
