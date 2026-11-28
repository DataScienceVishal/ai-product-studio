# Review: T-212 (branch `p/sme-council-tender-drafting/T-212`, commit abc805d)

Reviewer: reviewer agent, 2026-11-28. Diff reviewed: `git diff origin/main...abc805d` (6 files: build_docx.py, new test_tender_build_docx.py, S08 .md and .docx, SOURCES.md, NEXT.md).

## Verdict: PASS

## Summary

The T-194 review leftovers are all done, and the S08 demo-pack fix agrees with the rest of the pack text.

1. **Heading kept with a table** (build_docx.py:164-167): if the heading run plus the next table would go past `TABLE_PAGE_WORDS`, the break now goes before the heading. Tests cover the forcing case, the case where the table fits, and a run of headings.
2. **`--check` compares content** (build_docx.py:207-270): it rebuilds into a `TemporaryDirectory`, compares `fingerprint()` (core properties, footer, and each paragraph's style, runs, bold and page-break flags, plus each table cell), exits 1 on drift or a missing file, and never writes into `packs/`. It ignores zip bytes, which is right because python-docx timestamps zip members.
3. **Only `#{1,3} ` lines are headings** (`_HEADING` regex). `#5 x`, `#### x`, `#tag`, `##` and `#` stay plain text, and the parametrized tests cover each one.
4. **Table budget**: `TABLE_PAGE_WORDS = 900` is named and documented, and the behaviour is the same as before (it was `PAGE_WORDS * 2`).
5. **19 new unit tests** check behaviour: page layout through the fingerprint, drift detection, the CLI exit code, and that the CLI does not write the files (mtime check). Ragged rows, bold cells and repeated page breaks are covered too.
6. **S08 Appendix 1** gains the row "Other sites | 5 | 0 | Alarm only".

## Evidence

- `python3.13 demo-data/pack-sources/build_docx.py --check` exits 0 with "all committed .docx match their sources". So the new builder reproduces S01-S07 and S09-S12 content-identically, and none of those files is in the diff (`git diff --stat` touches only the S08 .docx under `demo-data/packs`).
- `eval/` is not touched at all: there is no diff under `eval/keys` or `eval/results`, `FROZEN.sha256` is unchanged, and `retrieval_labels.json` is unchanged, so its wording is verbatim.
- Old and new S08 .docx compared with `fingerprint()`: both have 94 blocks and only block 84 (the Appendix 1 table) differs. The page index of every block is identical, so S08 retrieval labels and page references are unaffected, and it is still 10 pages.
- S08 consistency:
  - Appendix 1 sites now sum to 3+1+1+5+4+5 = 19, matching the 19 alarm sites in 3.2 and "keys for all 19 sites" in 3.3.
  - The 3.3 categories match too: Cat 1 is market plus leisure (4), Cat 2 is business centre plus industrial (6), Cat 3 is halls plus other sites (4+5 = 9).
  - Cameras still sum to 74+22+12+10+20+0 = 138.
- The SOURCES.md hash `f13e0bd3b1fd9bf8` equals the first 16 characters of the sha256 of the new S08 .md, which is what the column records.
- Full backend suite on the exact branch tree, fresh Postgres DB (`t212_review`), python3.13, `-o addopts=""`: **1295 passed, 1 skipped, 0 failed in 314 s** (exit 0).

## Critical issues

None.

## Suggestions (non-blocking)

**S1. A table over 900 words now strands its heading alone on a page** (build_docx.py:164-167 and 180-181). When the table alone exceeds `TABLE_PAGE_WORDS`, three things happen:

1. The heading check breaks before the heading.
2. On the new page `on_page` holds the heading's words.
3. The table check (`on_page + n > TABLE_PAGE_WORDS`) breaks again.

So the heading sits alone on a page. Reproduced: 100 words, then `## Big`, then a 950-word table gives page 1 = text, page 2 = the heading only, page 3 = the table. Before this change the heading stayed at the foot of page 1, so for this case the result is slightly worse. A run of headings before a table of about 890 or more words splits the same way (the second heading re-runs the check with the first heading's words already on the page).

This is latent only: the largest table in any pack is 397 words (S08), and `--check` proves no committed pack changes.

Fix: skip the table-forced break when the page holds only the headings just placed, for example by tracking `heading_words_on_page` and testing `on_page - heading_words_on_page > 0`. Add a test with a table over 900 words.

**S2. S08 CCTV site count is a pre-existing soft inconsistency** (not introduced here). Appendix 1 lists 14 sites with cameras (3+1+1+5+4) against "11 CCTV sites" in 3.2 and Lot 1. Only "Other sites" (5) is alarm-only, while Lot 2 prices 8 alarm-only sites. The paragraph saying sites are "counted per system, not per building" papers over this. It is fine for a demo pack, but if R1 recording will show Appendix 1, consider making the camera-site count reconcile to 11 with 8 alarm-only. That is a .md edit only, S08 has no frozen key, and the retrieval label text is unaffected.

**S3. `test_check_cli_passes_on_the_committed_packs_and_does_not_write_them` makes the backend suite fail whenever a pack source is edited without a rebuild.** This is intended and good, but say so in the build_docx.py docstring or NEXT.md ("edit .md, then run build_docx.py, then commit both"), so the next builder is not surprised. The test also takes about 4 s because it builds all 12 packs, which is acceptable.

**S4. `fingerprint()` ignores fonts, table style and section settings.** That is acceptable for page-reference stability, but a change to the `Normal` font or size would pass `--check` while changing how Word shows the pages. Consider adding `document.styles["Normal"].font.name` and `.size` to the props entry.
