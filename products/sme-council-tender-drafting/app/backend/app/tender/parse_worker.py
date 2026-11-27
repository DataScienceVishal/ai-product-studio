"""Sandboxed document parser (DESIGN 4.1). Run as a standalone script by absolute path:

    python -I /app/app/tender/parse_worker.py <pdf|docx|txt> <input-file> <max-pages>

with an empty environment. It imports only the standard library, pypdf and python-docx, never `app` (`-I` drops the
working directory from sys.path). It sets its own resource limits before importing the parsers, prints one JSON
object on stdout and exits 0 for both success and a clean refusal:

    {"ok": true, "page_mode": "...", "pages": [{"text": "...", "headings": [...]}]}
    {"ok": false, "code": "<fixed refusal code>"}

Any crash, timeout or limit hit is turned into `parse_failed` by the caller."""
from __future__ import annotations

import json
import re
import sys
import unicodedata

MAX_AS_BYTES = 512 * 1024 * 1024
MAX_CPU_SECONDS = 30
ZIP_MAX_ENTRIES = 2000
ZIP_MAX_UNCOMPRESSED = 50 * 1024 * 1024
ZIP_MAX_RATIO = 100
BLOCK_WORDS = 400  # a "page" of a DOCX without page breaks, or of a text file, is a block of paragraphs
IMAGE_ONLY_CHARS = 30
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f﻿]")


class Refuse(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", _CONTROL.sub("", text))


def set_limits() -> None:
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (MAX_AS_BYTES, MAX_AS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS))


def blocks(paragraphs: list[tuple[str, bool]]) -> list[dict]:
    """Group (text, is_heading) paragraphs into blocks of about BLOCK_WORDS words."""
    pages, cur, words, heads = [], [], 0, []
    for text, is_head in paragraphs:
        n = len(text.split())
        if cur and words + n > BLOCK_WORDS:
            pages.append({"text": "\n\n".join(cur), "headings": heads})
            cur, words, heads = [], 0, []
        cur.append(text)
        words += n
        if is_head:
            heads.append(text)
    if cur:
        pages.append({"text": "\n\n".join(cur), "headings": heads})
    return pages


def parse_txt(path: str) -> tuple[str, list[dict]]:
    raw = open(path, "rb").read()
    if b"\x00" in raw:
        raise Refuse("unsupported_type")
    try:
        text = raw.decode("utf-8")  # strict
    except UnicodeDecodeError:
        raise Refuse("unsupported_type")
    paragraphs = [(p.strip(), False) for p in re.split(r"\n\s*\n", clean(text)) if p.strip()]
    return "text_block", blocks(paragraphs)


def parse_pdf(path: str, max_pages: int) -> tuple[str, list[dict]]:
    from pypdf import PdfReader
    reader = PdfReader(path, strict=False)
    if reader.is_encrypted:
        raise Refuse("encrypted")
    if len(reader.pages) > max_pages:
        raise Refuse("too_many_pages")
    return "pdf_page", [{"text": clean(page.extract_text() or "").strip(), "headings": []} for page in reader.pages]


def check_zip(path: str) -> None:
    import zipfile
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise Refuse("unsupported_type")
    with zf:
        infos = zf.infolist()
        if len(infos) > ZIP_MAX_ENTRIES:
            raise Refuse("zip_bomb")
        total = 0
        for info in infos:
            total += info.file_size
            ratio_bomb = info.file_size > 1024 and info.file_size > ZIP_MAX_RATIO * max(info.compress_size, 1)
            if total > ZIP_MAX_UNCOMPRESSED or ratio_bomb:
                raise Refuse("zip_bomb")
        names = {i.filename for i in infos}
        if any(n.lower().endswith("vbaproject.bin") for n in names):
            raise Refuse("macro_file")
        if "word/document.xml" not in names:
            raise Refuse("unsupported_type")
        for info in infos:  # no DTDs or entities anywhere in the XML (XXE, billion laughs): refuse outright
            if info.filename.endswith((".xml", ".rels")):
                head = zf.read(info.filename)
                if b"<!DOCTYPE" in head.upper() or b"<!ENTITY" in head.upper():
                    raise Refuse("xml_entities")


def parse_docx(path: str) -> tuple[str, list[dict]]:
    check_zip(path)
    import docx  # python-docx's parser is built with resolve_entities=False
    from docx.oxml.ns import qn
    document = docx.Document(path)
    pages: list[list[tuple[str, bool]]] = [[]]
    saw_break = False

    def para_text(p) -> str:
        return clean(p.text).strip()

    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            from docx.text.paragraph import Paragraph
            p = Paragraph(child, document)
            if child.xpath("./w:pPr/w:pageBreakBefore"):
                saw_break = True
                pages.append([])
            text = para_text(p)
            is_head = (p.style is not None and (p.style.name or "").lower().startswith(("heading", "title")))
            if text:
                pages[-1].append((text, is_head))
            if child.xpath(".//w:br[@w:type='page']"):
                saw_break = True
                pages.append([])
        elif child.tag == qn("w:tbl"):
            from docx.table import Table
            for row in Table(child, document).rows:
                cells = [clean(c.text).strip() for c in row.cells]
                line = " | ".join(c for c in cells if c)
                if line:
                    pages[-1].append((line, False))
    if saw_break:
        out = [{"text": "\n\n".join(t for t, _ in page), "headings": [t for t, h in page if h]} for page in pages if page]
        return "docx_break", out
    return "docx_block", blocks(pages[0])


def main(argv: list[str]) -> int:
    kind, path, max_pages = argv[1], argv[2], int(argv[3])
    set_limits()
    try:
        if kind == "pdf":
            mode, pages = parse_pdf(path, max_pages)
        elif kind == "docx":
            mode, pages = parse_docx(path)
        elif kind == "txt":
            mode, pages = parse_txt(path)
        else:
            raise Refuse("unsupported_type")
        if len(pages) > max_pages:
            raise Refuse("too_many_pages")
        result = {"ok": True, "page_mode": mode, "pages": pages}
    except Refuse as refusal:
        result = {"ok": False, "code": refusal.code}
    except BaseException as exc:  # includes MemoryError at the RLIMIT_AS ceiling; no document text in the message
        result = {"ok": False, "code": "parse_failed", "detail": type(exc).__name__}
    sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
