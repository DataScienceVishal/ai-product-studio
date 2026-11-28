"""Build the synthetic tender packs (.docx) from their Markdown sources (T-194, Q-20 option B). No model calls.

    python3 demo-data/pack-sources/build_docx.py            # writes demo-data/packs/S*.docx
    python3 demo-data/pack-sources/build_docx.py --check    # rebuilds into a temp dir and reports page/word counts

Supported Markdown: '#', '##', '###' headings, paragraphs, '- ' bullets, '1. ' numbered items, pipe tables
(header row plus a '|---|' separator), **bold** spans, and a '---pagebreak---' line. Anything else is kept as plain text.

Pages: a real page break is written at each '---pagebreak---' and whenever about PAGE_WORDS words have gone onto the
current page (at a paragraph or table boundary), so the app's parser (docx_break mode) sees A4-sized pages and the
page references in answer keys are stable. Every page carries a 'Synthetic demo document - fictional buyer' footer.
The build is deterministic: core properties are fixed, so the same source gives the same file text.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import tempfile
from pathlib import Path

import docx
from docx.enum.text import WD_BREAK
from docx.shared import Pt

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "packs"
PAGE_WORDS = 450
FOOTER = "Synthetic demo document - fictional buyer. Written by AI Product Studio for testing; not a real procurement."
FIXED_TIME = dt.datetime(2026, 11, 28, 0, 0, 0)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_NUM = re.compile(r"^\d+\.\s+")
_SEP = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


def _runs(paragraph, text: str) -> None:
    pos = 0
    for m in _BOLD.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos:m.start()])
        paragraph.add_run(m.group(1)).bold = True
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def _cells(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _blocks(md: str):
    """Yield (kind, payload) blocks: heading (level, text), para text, bullet text, number text, table rows, pagebreak."""
    lines = md.replace("\r\n", "\n").split("\n")
    i, para = 0, []

    def flush():
        if para:
            text = " ".join(s.strip() for s in para)
            para.clear()
            return ("para", text)
        return None

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s == "---pagebreak---":
            if (b := flush()):
                yield b
            yield ("pagebreak", None)
        elif not s:
            if (b := flush()):
                yield b
        elif s.startswith("#"):
            if (b := flush()):
                yield b
            level = len(s) - len(s.lstrip("#"))
            yield ("heading", (min(level, 3), s[level:].strip()))
        elif s.startswith("|") and i + 1 < len(lines) and _SEP.match(lines[i + 1].strip()):
            if (b := flush()):
                yield b
            rows = [_cells(s)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            yield ("table", rows)
            continue
        elif s.startswith(("- ", "* ")):
            if (b := flush()):
                yield b
            yield ("bullet", s[2:].strip())
        elif _NUM.match(s):
            if (b := flush()):
                yield b
            yield ("number", s)
        else:
            para.append(s)
        i += 1
    if (b := flush()):
        yield b


def _words(kind, payload) -> int:
    if kind == "table":
        return sum(len(c.split()) for row in payload for c in row)
    if kind == "heading":
        return len(payload[1].split())
    if kind == "pagebreak" or payload is None:
        return 0
    return len(payload.split())


def build(src: Path, dest: Path) -> dict:
    document = docx.Document()
    style = document.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10.5)
    props = document.core_properties
    props.author = "AI Product Studio (synthetic)"
    props.title = src.stem
    props.created = props.modified = FIXED_TIME
    props.last_modified_by = "AI Product Studio"
    props.revision = 1
    document.sections[0].footer.paragraphs[0].text = FOOTER

    pages, on_page, last = 1, 0, None

    def page_break():
        nonlocal pages, on_page
        if last is not None:
            run = document.paragraphs[-1].add_run() if document.paragraphs else document.add_paragraph().add_run()
            run.add_break(WD_BREAK.PAGE)
            pages += 1
            on_page = 0

    total = 0
    for kind, payload in _blocks(src.read_text(encoding="utf-8")):
        if kind == "pagebreak":
            if on_page:
                page_break()
            continue
        n = _words(kind, payload)
        if on_page and on_page + n > PAGE_WORDS and kind != "table":
            page_break()
        if kind == "heading":
            level, text = payload
            document.add_heading(_BOLD.sub(r"\1", text), level=level)
        elif kind == "para":
            _runs(document.add_paragraph(), payload)
        elif kind == "bullet":
            _runs(document.add_paragraph(style="List Bullet"), payload)
        elif kind == "number":
            _runs(document.add_paragraph(), payload)  # keep the number as typed: buyers' own numbering is data
        elif kind == "table":
            if on_page and on_page + n > PAGE_WORDS * 2:
                page_break()
            width = max(len(r) for r in payload)
            table = document.add_table(rows=0, cols=width)
            table.style = "Table Grid"
            for r, row in enumerate(payload):
                cells = table.add_row().cells
                for c in range(width):
                    text = row[c] if c < len(row) else ""
                    p = cells[c].paragraphs[0]
                    if r == 0:
                        p.add_run(_BOLD.sub(r"\1", text)).bold = True
                    else:
                        _runs(p, text)
            document.add_paragraph()
        on_page += n
        total += n
        last = kind
    dest.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(dest))
    return {"file": dest.name, "pages": pages, "words": total}


def sources() -> list[Path]:
    return sorted(HERE.glob("S[0-9][0-9]-*.md"))


def main(argv: list[str]) -> int:
    out = Path(tempfile.mkdtemp()) if "--check" in argv else OUT
    for src in sources():
        r = build(src, out / (src.stem + ".docx"))
        print(f"{r['file']}: {r['pages']} pages, {r['words']} words")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
