"""Upload handling around the sandboxed parser: magic-byte sniffing, running the worker, refusal codes (DESIGN 4.1)."""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass

log = logging.getLogger("app.tender.ingest")
WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parse_worker.py")
WALL_TIMEOUT_SECONDS = 45
MAX_WORKER_OUTPUT = 40 * 1024 * 1024
IMAGE_ONLY_CHARS = 30
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # old .doc, and the container of password-protected DOCX

# fixed refusal code -> (HTTP status, message shown to the user)
REFUSALS: dict[str, tuple[int, str]] = {
    "unsupported_type": (415, "That file type isn't supported. Upload a PDF or a Word (.docx) file."),
    "unsupported_tender_type": (415, "Tender files must be PDF or Word (.docx). Plain text is accepted for the evidence library only."),
    "encrypted": (422, "That file is password-protected. Remove the password and upload it again."),
    "macro_file": (422, "Word files with macros (.docm) aren't accepted. Save it as a plain .docx and upload it again."),
    "zip_bomb": (422, "That file is unusually large once unpacked, so it was refused."),
    "xml_entities": (422, "That file contains XML entity or DTD definitions, so it was refused."),
    "too_many_pages": (422, "That file has too many pages (the limit is 60 per file)."),
    "image_only": (422, "Scanned pages are not supported in this demo. Upload a file with selectable text."),
    "parse_failed": (422, "We couldn't read that file. Check it opens normally and try again."),
}


class Refused(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
        self.status, self.message = REFUSALS[code]


@dataclass
class Parsed:
    kind: str  # pdf | docx | txt
    mime: str
    page_mode: str
    pages: list[dict]  # {"text": str, "headings": [str]}


MIME = {"pdf": "application/pdf", "txt": "text/plain",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def sniff(data: bytes, *, allow_text: bool) -> str:
    """The kind by magic bytes, never by extension. Raises Refused for anything else."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        return "docx"  # the worker confirms word/document.xml and refuses macros
    if data.startswith(OLE_MAGIC):
        raise Refused("encrypted")  # password-protected DOCX is an OLE file; a legacy .doc is refused the same way
    if allow_text:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise Refused("unsupported_type")
        if "\x00" in text or not text.strip():
            raise Refused("unsupported_type")
        return "txt"
    if data[:8192].count(b"\x00") == 0:
        try:
            data[:8192].decode("utf-8")
            raise Refused("unsupported_tender_type")
        except UnicodeDecodeError:
            pass
    raise Refused("unsupported_type")


def run_worker(kind: str, data: bytes, max_pages: int) -> dict:
    """Write the bytes to a temp file, parse in a child process, delete the file. Never raises for a bad document."""
    with tempfile.TemporaryDirectory(prefix="tender-parse-") as tmp:
        path = os.path.join(tmp, "input." + kind)
        with open(path, "wb") as fh:
            fh.write(data)
        try:
            done = subprocess.run([sys.executable, "-I", WORKER, kind, path, str(max_pages)], env={}, cwd=tmp,
                                  stdin=subprocess.DEVNULL, capture_output=True, timeout=WALL_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            log.warning("parse worker timed out")
            return {"ok": False, "code": "parse_failed"}
        except OSError:
            log.exception("parse worker could not start")
            return {"ok": False, "code": "parse_failed"}
    if done.returncode != 0 or len(done.stdout) > MAX_WORKER_OUTPUT:
        log.warning("parse worker failed", extra={"returncode": done.returncode})
        return {"ok": False, "code": "parse_failed"}
    try:
        result = json.loads(done.stdout)
    except ValueError:
        return {"ok": False, "code": "parse_failed"}
    return result if isinstance(result, dict) else {"ok": False, "code": "parse_failed"}


def parse_upload(data: bytes, *, allow_text: bool, max_pages: int) -> Parsed:
    kind = sniff(data, allow_text=allow_text)
    result = run_worker(kind, data, max_pages)
    if not result.get("ok"):
        code = result.get("code")
        raise Refused(code if code in REFUSALS else "parse_failed")
    pages = result["pages"]
    total = sum(len(p["text"].strip()) for p in pages)
    if not pages or total < IMAGE_ONLY_CHARS:
        raise Refused("image_only")
    return Parsed(kind=kind, mime=MIME[kind], page_mode=result["page_mode"], pages=pages)


def is_image_only_page(kind: str, text: str) -> bool:
    return kind == "pdf" and len(text.strip()) < IMAGE_ONLY_CHARS


_SAFE = re.compile(r"[\x00-\x1f\x7f/\\]")


def clean_filename(name: str | None) -> str:
    base = _SAFE.sub("", (name or "").replace("\\", "/").split("/")[-1]).strip().lstrip(".")
    return (base or "document")[:255]
