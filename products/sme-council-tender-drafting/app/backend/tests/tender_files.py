"""Fixture files built in code (no binary blobs): PDFs, DOCX, text and the crafted bad files for each refusal."""
from __future__ import annotations

import io
import zipfile

import docx
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

LOREM = ("Our team delivers this service with trained staff, documented procedures, regular audits and a clear "
         "escalation route for the client. ")


def words(n: int, seed: str = "") -> str:
    base = (seed + " " + LOREM * (n // 20 + 1)).split()
    return " ".join(base[:n]) + "."


def pdf(pages: list[list[str]]) -> bytes:
    """One PDF page per list of lines (each line drawn on its own row)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))
    for lines in pages:
        y = 800
        for line in lines:
            c.setFont("Helvetica", 10)
            c.drawString(40, y, line)
            y -= 14
        c.showPage()
    c.save()
    return buf.getvalue()


def wrap(text: str, width: int = 90) -> list[str]:
    out, cur = [], ""
    for w in text.split():
        if len(cur) + len(w) + 1 > width:
            out.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    return out + ([cur] if cur else [])


def image_only_pdf(pages: int = 2) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(595, 842))
    for _ in range(pages):
        c.rect(50, 50, 400, 400, fill=1)
        c.showPage()
    c.save()
    return buf.getvalue()


def encrypted_pdf() -> bytes:
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf([["Confidential tender text " * 3]]))))
    writer.encrypt("secret", algorithm="RC4-128")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def docx_bytes(paragraphs: list[tuple[str, str | None]], page_break_after: set[int] = frozenset()) -> bytes:
    """paragraphs: (text, style) where style None means Normal or "Heading 1"."""
    d = docx.Document()
    for i, (text, style) in enumerate(paragraphs):
        d.add_paragraph(text, style=style)
        if i in page_break_after:
            d.add_page_break()
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _rewrite(data: bytes, replace: dict[str, bytes] | None = None, add: dict[str, bytes] | None = None) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info.filename, (replace or {}).get(info.filename, src.read(info.filename)))
        for name, body in (add or {}).items():
            dst.writestr(name, body)
    return out.getvalue()


def docm_bytes() -> bytes:
    return _rewrite(docx_bytes([(words(60), None)]), add={"word/vbaProject.bin": b"\x00fake macro project"})


def zip_bomb_bytes() -> bytes:
    """A valid-looking DOCX whose extra entry inflates 120 MB from a few hundred KB (ratio over 100, total over 50 MB)."""
    return _rewrite(docx_bytes([(words(60), None)]), add={"word/media/pad.bin": b"\x00" * (120 * 1024 * 1024)})


def many_entries_bytes() -> bytes:
    return _rewrite(docx_bytes([(words(60), None)]), add={f"word/pad/{i}.txt": b"x" for i in range(2100)})


XXE = (b'<?xml version="1.0"?><!DOCTYPE doc [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
       b'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
       b'<w:p><w:r><w:t>&xxe; tender text that is long enough to count as real content</w:t></w:r></w:p></w:body></w:document>')


def xxe_docx() -> bytes:
    return _rewrite(docx_bytes([(words(60), None)]), replace={"word/document.xml": XXE})


OLE_BYTES = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 600  # password-protected DOCX / legacy .doc container
