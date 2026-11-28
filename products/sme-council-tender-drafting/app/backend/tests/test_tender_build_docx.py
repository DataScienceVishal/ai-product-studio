"""Unit tests for the synthetic tender-pack builder (demo-data/pack-sources/build_docx.py, T-194/T-212). No DB, no model.

Covers: heading kept with a following table, the T-218 CLI guard (--write, --only, frozen packs), --check against the committed files, '#{1,3} ' headings only,
the table page budget, and the faithfulness cases from the T-194 review (ragged rows, bold in cells, repeated pagebreaks).
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import docx
import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("build_docx", ROOT / "demo-data" / "pack-sources" / "build_docx.py")
bd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bd)


def words(n: int, tag: str = "w") -> str:
    return " ".join(f"{tag}{i}" for i in range(n))


def make(tmp_path: Path, md: str, name: str = "S99-test.md") -> Path:
    src = tmp_path / name
    src.write_text(md, encoding="utf-8")
    return src


def pages_of(path: Path) -> list[list[str]]:
    """Texts of body blocks per page (a page break run ends a page)."""
    out, cur = [], []
    for kind, *rest in bd.fingerprint(path)[2:]:
        if kind == "p":
            style, runs = rest
            text = "".join(r[0] for r in runs)
            if text:
                cur.append(f"[{style}] {text}")
            if any(r[2] for r in runs):
                out.append(cur)
                cur = []
        else:
            cur.append("[table]")
    out.append(cur)
    return out


# --- 1. a heading is not stranded before a table that forces a break -------------------------------------------
def test_heading_moves_to_the_next_page_with_a_table_that_forces_a_break(tmp_path):
    big = "| a | b |\n|---|---|\n| " + words(500, "x") + " | " + words(300, "y") + " |\n"
    md = words(440, "p") + "\n\n## Pricing\n\n" + big
    bd.build(make(tmp_path, md), tmp_path / "S99-test.docx")
    pages = pages_of(tmp_path / "S99-test.docx")
    assert len(pages) == 2
    assert not any("Pricing" in b for b in pages[0]), "heading stranded at the foot of page 1"
    assert pages[1][0] == "[Heading 2] Pricing" and pages[1][1] == "[table]"


def test_heading_stays_when_the_table_fits(tmp_path):
    md = words(100, "p") + "\n\n## Pricing\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    bd.build(make(tmp_path, md), tmp_path / "S99-test.docx")
    assert len(pages_of(tmp_path / "S99-test.docx")) == 1


def test_a_run_of_headings_before_a_forcing_table_moves_together(tmp_path):
    big = "| a |\n|---|\n| " + words(800, "x") + " |\n"
    md = words(300, "p") + "\n\n# One\n\n## Two\n\n" + big
    bd.build(make(tmp_path, md), tmp_path / "S99-test.docx")
    pages = pages_of(tmp_path / "S99-test.docx")
    assert [b for b in pages[0] if "Heading" in b] == []
    assert pages[1][:3] == ["[Heading 1] One", "[Heading 2] Two", "[table]"]


# --- 3. only '#{1,3} ' is a heading -------------------------------------------------------------------------
@pytest.mark.parametrize("line", ["#5 Lot reference", "#### Four hashes", "#hashtag", "##", "#"])
def test_hash_lines_without_hash_space_are_plain_text(line):
    assert list(bd._blocks(line)) == [("para", line)]


@pytest.mark.parametrize("line,level,text", [("# A", 1, "A"), ("## B c", 2, "B c"), ("### D", 3, "D")])
def test_real_headings(line, level, text):
    assert list(bd._blocks(line)) == [("heading", (level, text))]


def test_hash_line_keeps_its_hash_in_the_docx(tmp_path):
    bd.build(make(tmp_path, "#5 Lot reference\n"), tmp_path / "S99-test.docx")
    assert "#5 Lot reference" in [p.text for p in docx.Document(str(tmp_path / "S99-test.docx")).paragraphs]


# --- 4. page budget: 450 words for text, tables up to about 900 on a page ----------------------------------
def test_page_budget_constants():
    assert bd.PAGE_WORDS == 450 and bd.TABLE_PAGE_WORDS == 900


def test_text_breaks_at_450_words_and_a_table_may_take_the_page_to_900(tmp_path):
    para = words(200, "p")
    table = "| a |\n|---|\n| " + words(600, "t") + " |\n"
    # 200 text + 600 table = 800 <= 900: the table stays; a further 200-word paragraph passes 450 and breaks.
    bd.build(make(tmp_path, para + "\n\n" + table + "\n" + para + "\n"), tmp_path / "S99-test.docx")
    assert len(pages_of(tmp_path / "S99-test.docx")) == 2
    # 200 text + 750 table = 950 > 900: the table starts its own page.
    t2 = "| a |\n|---|\n| " + words(750, "t") + " |\n"
    bd.build(make(tmp_path, para + "\n\n" + t2, "S98-test.md"), tmp_path / "S98-test.docx")
    pg = pages_of(tmp_path / "S98-test.docx")
    assert len(pg) == 2 and pg[1] == ["[table]"]


# --- faithfulness cases from the T-194 review --------------------------------------------------------------
def test_ragged_rows_bold_cells_and_repeated_pagebreaks(tmp_path):
    md = ("---pagebreak---\nIntro\n\n| h1 | h2 |\n|:---|---:|\n| a | b | c |\n| only |\n|  | **bold** x |\n\n"
          "---pagebreak---\n---pagebreak---\nTail 1. kept\n\n1. Numbered\n- bullet\n")
    bd.build(make(tmp_path, md), tmp_path / "S99-test.docx")
    d = docx.Document(str(tmp_path / "S99-test.docx"))
    t = d.tables[0]
    assert len(t.rows[0].cells) == 3
    assert [c.text for c in t.rows[2].cells] == ["only", "", ""]
    assert t.rows[3].cells[1].paragraphs[0].runs[0].bold
    assert all(r.bold for r in t.rows[0].cells[0].paragraphs[0].runs)
    assert "1. Numbered" in [p.text for p in d.paragraphs]  # number kept as typed
    assert len(pages_of(tmp_path / "S99-test.docx")) == 2  # leading and repeated pagebreaks add no empty page


# --- 2. --check compares content with the committed files -------------------------------------------------
def test_check_passes_for_a_matching_file_and_fails_on_drift(tmp_path):
    src = make(tmp_path, "## H\n\nBody text\n")
    packs = tmp_path / "packs"
    bd.build(src, packs / "S99-test.docx")
    assert bd.check(tmp_path / "w1", packs, [src]) == []
    src.write_text("## H\n\nBody text changed\n", encoding="utf-8")  # source edited, .docx not rebuilt
    problems = bd.check(tmp_path / "w2", packs, [src])
    assert len(problems) == 1 and "differs" in problems[0]
    assert "no committed file" in bd.check(tmp_path / "w3", tmp_path / "empty", [src])[0]


def test_check_ignores_zip_bytes(tmp_path):
    src = make(tmp_path, "Body\n")
    a, b = tmp_path / "a.docx", tmp_path / "b.docx"
    bd.build(src, a)
    bd.build(src, b)
    assert bd.fingerprint(a) == bd.fingerprint(b)


def test_check_cli_passes_on_the_committed_packs_and_does_not_write_them():
    before = {p.name: p.stat().st_mtime_ns for p in bd.OUT.glob("*.docx")}
    r = subprocess.run([sys.executable, str(ROOT / "demo-data" / "pack-sources" / "build_docx.py"), "--check"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert {p.name: p.stat().st_mtime_ns for p in bd.OUT.glob("*.docx")} == before


# --- 6. S08 Appendix 1 is consistent with 19 alarm sites -------------------------------------------------
def test_s08_appendix_1_lists_19_sites():
    md = (ROOT / "demo-data" / "pack-sources" / "S08-security-trust-cctv-keyholding.md").read_text(encoding="utf-8")
    app = md.split("## Appendix 1")[1].split("\n## ")[0]
    rows = [r for r in bd._blocks(app) if r[0] == "table"][0][1][1:]
    assert sum(int(r[1]) for r in rows) == 19 == int(re.search(r"(\d+) sites with intruder alarm panels", md).group(1))
    assert sum(int(r[2]) for r in rows) == 138


# --- T-217: a table over the page budget must not leave its heading alone on a page ------------------------------
@pytest.mark.parametrize("heads", ["## Big\n\n", "# One\n\n## Two\n\n"])
def test_oversize_table_does_not_strand_its_heading_alone(tmp_path, heads):
    big = "| a |\n|---|\n| " + words(950, "x") + " |\n"
    md = words(100, "p") + "\n\n" + heads + big
    bd.build(make(tmp_path, md), tmp_path / "S99-test.docx")
    pages = pages_of(tmp_path / "S99-test.docx")
    for pg in pages:
        assert any("[table]" == b or "[Normal]" in b or "[List" in b for b in pg), f"page holds only headings: {pg}"
    assert len(pages) == 2 and pages[1][-1] == "[table]" and pages[1][0].startswith("[Heading")


def test_oversize_table_at_the_top_of_a_page_keeps_one_page(tmp_path):
    big = "| a |\n|---|\n| " + words(950, "x") + " |\n"
    bd.build(make(tmp_path, "## Big\n\n" + big), tmp_path / "S99-test.docx")
    assert len(pages_of(tmp_path / "S99-test.docx")) == 1


# --- T-218: the CLI never writes by accident, and frozen held-out packs are protected ---------------------------
BUILDER = ROOT / "demo-data" / "pack-sources" / "build_docx.py"
DEMO = {"S04-cleaning-halls-and-toilets.docx", "S08-security-trust-cctv-keyholding.docx", "S12-grounds-hallowby-town.docx"}


def _packs_state() -> dict:
    return {p.name: p.stat().st_mtime_ns for p in bd.OUT.glob("*.docx")}


@pytest.mark.parametrize("args,code", [([], 2), (["--help"], 0), (["-h"], 0), (["--bogus"], 2),
                                       (["--allow-frozen"], 2), (["--only", "S08"], 2),
                                       (["--check", "--only", "S08"], 2), (["--check", "--write"], 2),
                                       (["--write", "--only", "S01"], 2), (["--write", "--only", "S99"], 2)])
def test_cli_refuses_without_writing(args, code):
    before = _packs_state()
    r = subprocess.run([sys.executable, str(BUILDER), *args], capture_output=True, text=True, timeout=120)
    assert r.returncode == code, (r.stdout, r.stderr)
    assert _packs_state() == before


def test_frozen_names_are_the_nine_held_out_packs():
    frozen = bd.frozen_names()
    all_packs = {p.stem + ".docx" for p in bd.sources()}
    assert len(frozen) == 9 and frozen <= all_packs and all_packs - frozen == DEMO


def test_plan_writes_skips_frozen_unless_allowed():
    todo, skipped, errors = bd.plan_writes(None, False)
    assert {s.stem + ".docx" for s in todo} == DEMO and len(skipped) == 9 and not errors
    todo, skipped, errors = bd.plan_writes(None, True)
    assert len(todo) == 12 and not skipped and not errors
    todo, skipped, errors = bd.plan_writes(["s08"], False)
    assert [s.stem[:3] for s in todo] == ["S08"] and not errors
    _, _, errors = bd.plan_writes(["S01", "S08"], False)
    assert errors and "allow-frozen" in errors[0]
    todo, _, errors = bd.plan_writes(["S01"], True)
    assert [s.stem[:3] for s in todo] == ["S01"] and not errors


def test_frozen_names_missing_list_is_empty(tmp_path):
    assert bd.frozen_names(tmp_path / "nope.sha256") == set()


def test_write_rewrites_only_demo_packs(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(bd, "OUT", tmp_path)
    assert bd.main(["build_docx.py", "--write"]) == 0
    assert {p.name for p in tmp_path.glob("*.docx")} == DEMO
    assert capsys.readouterr().out.count("skipped (frozen") == 9
    assert bd.check(tmp_path / "rebuild", packs=tmp_path, srcs=[s for s in bd.sources() if s.stem + ".docx" in DEMO]) == []


def test_write_allow_frozen_only_named(tmp_path, monkeypatch):
    monkeypatch.setattr(bd, "OUT", tmp_path)
    assert bd.main(["build_docx.py", "--write", "--only", "S01", "--allow-frozen"]) == 0
    assert [p.name for p in tmp_path.glob("*.docx")] == ["S01-cleaning-civic-offices-conveniences.docx"]


# --- T-218 (T-217 review S2): a long paragraph does not strand the headings above it ---------------------------
@pytest.mark.parametrize("heads", ["## Method\n\n", "# Part\n\n## Method\n\n"])
def test_long_paragraph_does_not_strand_headings(tmp_path, heads):
    md = words(300, "a") + "\n\n---pagebreak---\n\n" + heads + words(460, "p") + "\n\n" + words(20, "q")
    bd.build(make(tmp_path, md), tmp_path / "S99-test.docx")
    for pg in [pg for pg in pages_of(tmp_path / "S99-test.docx") if pg]:
        assert any(not b.startswith("[Heading") for b in pg), f"page holds only headings: {pg}"


# --- T-218 (T-217 review S3): pin the reconciled S08 numbers -------------------------------------------------
def test_s08_reconciled_counts():
    md = (ROOT / "demo-data" / "pack-sources" / "S08-security-trust-cctv-keyholding.md").read_text(encoding="utf-8")
    app = md.split("## Appendix 1")[1].split("\n## ")[0]
    rows = [r for r in bd._blocks(app) if r[0] == "table"][0][1][1:]
    cctv_sites = sum(int(r[1]) for r in rows if int(r[2]) > 0)
    alarm_only = sum(int(r[1]) for r in rows if int(r[2]) == 0)
    assert (cctv_sites, alarm_only) == (14, 5)
    assert "The Trust has 14 sites with 138 cameras" in md and "19 sites with intruder alarm panels" in md
    assert f"for {cctv_sites} CCTV sites | {cctv_sites * 12} site-months" in md
    assert f"for {alarm_only} alarm-only sites | {alarm_only * 12} site-months" in md
    assert "the 19 alarm sites and 14 CCTV sites" in md
    s33 = md.split("### 3.3")[1].split("\n### ")[0]
    cat = [r for r in bd._blocks(s33) if r[0] == "table"][0][1][1:]
    assert [int(r[1]) for r in cat] == [4, 6, 9] and sum(int(r[1]) for r in cat) == 19
    assert "hold keys for all 19 sites" in s33


def test_frozen_names_reads_binary_mode_lines(tmp_path):
    f = tmp_path / "F.sha256"
    f.write_text("ab *demo-data/packs/S01-x.docx\ncd  demo-data/packs/S02-y.docx\nef  eval/keys/a.json\n")
    assert bd.frozen_names(f) == {"S01-x.docx", "S02-y.docx"}


def test_plan_writes_fails_closed_without_a_frozen_list():
    todo, _, errors = bd.plan_writes(None, False, frozen=set())
    assert todo == [] and errors and "refusing" in errors[0]
    todo, _, errors = bd.plan_writes(None, True, frozen=set())
    assert len(todo) == 12 and not errors
