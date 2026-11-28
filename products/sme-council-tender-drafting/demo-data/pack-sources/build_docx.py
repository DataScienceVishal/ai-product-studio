"""Build the synthetic tender packs (.docx) from their Markdown sources (T-194, Q-20 option B). No model calls.

    python3 demo-data/pack-sources/build_docx.py --check                # rebuild into a temp dir, compare with packs/ (never writes)
    python3 demo-data/pack-sources/build_docx.py --write                # rewrite packs/S*.docx, skipping frozen held-out packs
    python3 demo-data/pack-sources/build_docx.py --write --only S08     # rewrite only the named pack(s)
    python3 demo-data/pack-sources/build_docx.py --write --allow-frozen # also rewrite the frozen packs (breaks FROZEN.sha256)
    python3 demo-data/pack-sources/build_docx.py --help

No arguments, or an unknown one, prints usage and exits 2 without writing anything (T-218). A pack is frozen when its
.docx is listed in eval/keys/FROZEN.sha256; --write skips it (and --only on a frozen pack fails) unless --allow-frozen.

Supported Markdown: '# ', '## ', '### ' headings (hashes followed by a space; '#5 ...' or '#### ...' stay plain text), paragraphs, '- ' bullets, '1. ' numbered items, pipe tables
(header row plus a '|---|' separator), **bold** spans, and a '---pagebreak---' line. Anything else is kept as plain text.

Pages: a real page break is written at each '---pagebreak---' and whenever about PAGE_WORDS (450) words have gone onto the
current page (at a paragraph boundary). Tables are the exception: a table is never split, so a page may carry up to
TABLE_PAGE_WORDS (900) words when a table is on it, and a table starts a new page only if it would take the page past
that. A heading is kept with the block after it: if the next block is a table that would force a break, the break goes
before the heading, so a heading is never stranded at the foot of a page. So the app's parser (docx_break mode) sees A4-sized pages and the
page references in answer keys are stable. Every page carries a 'Synthetic demo document - fictional buyer' footer.
The build is deterministic in content: core properties are fixed, so the same source gives the same file text. The zip
bytes are not compared (python-docx timestamps its zip members), `--check` compares `fingerprint()` instead: core
properties, footer, and every paragraph (style, runs with bold, page breaks) and table cell in order. It exits 1 on any
difference or a missing committed file. Only --write rewrites files; the frozen held-out packs are only touched with
--allow-frozen, and tests/CI use --check, which never writes into packs/.
"""
from __future__ import annotations

import argparse
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
FROZEN_LIST = HERE.parent.parent / "eval" / "keys" / "FROZEN.sha256"
PAGE_WORDS = 450
TABLE_PAGE_WORDS = PAGE_WORDS * 2  # a page holding a table may reach about 900 words (the reviewer's page-budget rule)
FOOTER = "Synthetic demo document - fictional buyer. Written by AI Product Studio for testing; not a real procurement."
FIXED_TIME = dt.datetime(2026, 11, 28, 0, 0, 0)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_HEADING = re.compile(r"^(#{1,3}) +(.*)$")
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
        elif (hm := _HEADING.match(s)):
            if (b := flush()):
                yield b
            yield ("heading", (len(hm.group(1)), hm.group(2).strip()))
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
    heads_on_page = 0  # words of the headings just placed that head this page (nothing else on it yet)

    def page_break():
        nonlocal pages, on_page, heads_on_page
        if last is not None:
            heads_on_page = 0
            run = document.paragraphs[-1].add_run() if document.paragraphs else document.add_paragraph().add_run()
            run.add_break(WD_BREAK.PAGE)
            pages += 1
            on_page = 0

    total = 0
    blocks = list(_blocks(src.read_text(encoding="utf-8")))
    for idx, (kind, payload) in enumerate(blocks):
        if kind == "pagebreak":
            if on_page:
                page_break()
            continue
        n = _words(kind, payload)
        need = n
        if kind == "heading":  # keep a heading with the start of what follows it, never stranded at a page foot
            j = idx + 1
            while j < len(blocks) and blocks[j][0] == "heading":  # a run of headings stays together too
                need += _words(*blocks[j])
                j += 1
            nxt = blocks[j] if j < len(blocks) else ("pagebreak", None)
            heads = need
            need += min(_words(*nxt), 80) if nxt[0] not in ("pagebreak", "table") else 0
            if nxt[0] == "table" and on_page + heads + _words(*nxt) > TABLE_PAGE_WORDS:
                need = PAGE_WORDS + 1  # the table will force its own break: break before the heading, not between
        only_heads = on_page == heads_on_page  # the page holds nothing but the headings just placed
        if on_page and on_page + need > PAGE_WORDS and kind != "table" and not only_heads:  # never strand headings alone
            page_break()
        only_heads = on_page == heads_on_page  # recomputed: the break above may have emptied the page
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
            if on_page and not only_heads and on_page + n > TABLE_PAGE_WORDS:  # never strand headings alone
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
        heads_on_page = on_page if kind == "heading" and only_heads else 0
        total += n
        last = kind
    dest.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(dest))
    return {"file": dest.name, "pages": pages, "words": total}


def sources() -> list[Path]:
    return sorted(HERE.glob("S[0-9][0-9]-*.md"))


def _para_print(p) -> list:
    runs = []
    for r in p.runs:
        brk = any(b.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type") == "page"
                  for b in r._r.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br"))
        runs.append([r.text, bool(r.bold), brk])
    return [p.style.name, runs]


def fingerprint(path: Path) -> list:
    """Deterministic content of a .docx: properties, footer, and body blocks in order (not zip bytes)."""
    d = docx.Document(str(path))
    cp = d.core_properties
    out: list = [["props", cp.author, cp.title, cp.created.isoformat() if cp.created else None, cp.last_modified_by, cp.revision],
                 ["footer", d.sections[0].footer.paragraphs[0].text]]
    body = d.element.body
    paras = {p._p: p for p in d.paragraphs}
    tables = {t._tbl: t for t in d.tables}
    for el in body.iterchildren():
        if el in paras:
            out.append(["p"] + _para_print(paras[el]))
        elif el in tables:
            out.append(["t", [[[_para_print(p) for p in c.paragraphs] for c in row.cells] for row in tables[el].rows]])
    return out


def first_difference(a: list, b: list) -> str | None:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f"block {i}: built {str(x)[:160]!r} != committed {str(y)[:160]!r}"
    if len(a) != len(b):
        return f"block count: built {len(a)} != committed {len(b)}"
    return None


def check(out_dir: Path, packs: Path = OUT, srcs: list[Path] | None = None) -> list[str]:
    """Build every source into out_dir and compare with packs/<name>.docx; return the problems found."""
    problems = []
    for src in (srcs if srcs is not None else sources()):
        built = out_dir / (src.stem + ".docx")
        r = build(src, built)
        print(f"{r['file']}: {r['pages']} pages, {r['words']} words")
        committed = packs / built.name
        if not committed.exists():
            problems.append(f"{built.name}: no committed file in {packs}")
            continue
        diff = first_difference(fingerprint(built), fingerprint(committed))
        if diff:
            problems.append(f"{built.name}: differs from the committed file ({diff})")
    return problems


def frozen_names(frozen_list: Path = FROZEN_LIST) -> set[str]:
    """Names of the .docx packs pinned in FROZEN.sha256 (the held-out packs)."""
    if not frozen_list.exists():
        return set()
    names = set()
    for line in frozen_list.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].startswith("demo-data/packs/") and parts[1].endswith(".docx"):
            names.add(Path(parts[1]).name)
    return names


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="build_docx.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="rebuild into a temp dir and compare; never writes packs/")
    mode.add_argument("--write", action="store_true", help="rewrite packs/S*.docx (frozen packs skipped)")
    ap.add_argument("--only", nargs="+", metavar="SNN", help="with --write: only these packs, e.g. S08 S12")
    ap.add_argument("--allow-frozen", action="store_true", help="with --write: also rewrite frozen held-out packs")
    return ap


def plan_writes(only: list[str] | None, allow_frozen: bool, srcs: list[Path] | None = None,
                frozen: set[str] | None = None) -> tuple[list[Path], list[str], list[str]]:
    """Return (sources to write, skipped frozen names, errors). Nothing is written here."""
    srcs = srcs if srcs is not None else sources()
    frozen = frozen if frozen is not None else frozen_names()
    errors: list[str] = []
    chosen = srcs
    if only:
        wanted = {o.upper() for o in only}
        chosen = [s for s in srcs if s.stem[:3].upper() in wanted]
        missing = wanted - {s.stem[:3].upper() for s in chosen}
        if missing:
            errors.append("no source for: " + ", ".join(sorted(missing)))
    todo, skipped = [], []
    for s in chosen:
        if (s.stem + ".docx") in frozen and not allow_frozen:
            skipped.append(s.stem + ".docx")
        else:
            todo.append(s)
    if only and skipped:
        errors.append("frozen held-out pack(s), rerun with --allow-frozen to rewrite: " + ", ".join(skipped))
    return todo, skipped, errors


def main(argv: list[str]) -> int:
    ap = _parser()
    try:
        args = ap.parse_args(argv[1:])
    except SystemExit as e:  # --help exits 0, a bad argument exits 2; neither writes
        return int(e.code or 0)
    if args.check:
        if args.only or args.allow_frozen:
            ap.print_usage(sys.stderr)
            print("build_docx.py: --only/--allow-frozen need --write", file=sys.stderr)
            return 2
        with tempfile.TemporaryDirectory() as tmp:
            problems = check(Path(tmp))
        for line in problems:
            print("DRIFT " + line, file=sys.stderr)
        print("check: " + ("FAILED, rebuild with build_docx.py --write" if problems else "all committed .docx match their sources"))
        return 1 if problems else 0
    if not args.write:
        ap.print_usage(sys.stderr)
        print("build_docx.py: nothing done; pass --check or --write (see --help)", file=sys.stderr)
        return 2
    todo, skipped, errors = plan_writes(args.only, args.allow_frozen)
    if errors:
        for e in errors:
            print("build_docx.py: " + e, file=sys.stderr)
        return 2
    for name in skipped:
        print(f"{name}: skipped (frozen held-out pack; --allow-frozen to rewrite)")
    for src in todo:
        r = build(src, OUT / (src.stem + ".docx"))
        print(f"{r['file']}: {r['pages']} pages, {r['words']} words")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
