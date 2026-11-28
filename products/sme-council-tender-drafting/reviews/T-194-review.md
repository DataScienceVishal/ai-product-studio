# Review: p/sme-council-tender-drafting/T-194 (synthetic tender packs)

Reviewer: reviewer agent, 2026-11-28. Diff: `git diff main...p/sme-council-tender-drafting/T-194` (30 files: 12 Markdown sources, 12 .docx, `build_docx.py`, `manifest.json`, SOURCES.md, SPEC.md and EVAL.md amendments, validator review).

**Verdict: PASS.** No critical issues. Five suggestions below. None of them blocks the merge.

## Summary

`build_docx.py` turns the 12 Markdown pack sources into .docx files. I parsed every committed .docx with the app's own parser (`python3 -I app/backend/app/tender/parse_worker.py docx <file> 40`) and compared the output with its .md source. Nothing is lost or duplicated, numbering is kept, and there are no empty pages. The manifest roles follow the SPEC rule, and the eval and seed loaders accept the manifest. The sources contain no personal data and no secrets.

## Evidence

**1. Text is kept in full.** A comparison script (scratchpad `cmp.py`) built two word sequences for each pack:
- from the raw .md, with `#`, `**`, bullet markers, pipes and `|---|` separators removed;
- from the parser's pages joined together.

The two sequences are identical for all 12 packs:

| Pack | Words | Pack | Words | Pack | Words |
|---|---|---|---|---|---|
| S01 | 4471 | S05 | 4444 | S09 | 4428 |
| S02 | 2204 | S06 | 2499 | S10 | 2142 |
| S03 | 2086 | S07 | 2341 | S11 | 2348 |
| S04 | 1547 | S08 | 2536 | S12 | 1808 |

The block-level sequence (headings, paragraphs, bullets, numbered lines, and table rows rendered as `a | b`) also matches exactly. So nothing is lost or duplicated, and nothing is reordered.

**2. Numbering is kept.** Numbered lines are written as typed in the Normal style, not as Word auto-numbering. So `1.`, `10.`, `1.1*`, `(a)` and `Q2 ... (5%)*` all reach the parser as written. Literal asterisks such as `1.1*` (questions marked with an asterisk) survive.

**3. Page breaks work.**
- Every pack parses in `docx_break` mode.
- The builder's page count equals the parser's page count, and both match the SOURCES.md table: 13, 8, 9, 7, 15, 10, 10, 10, 13, 7, 9, 7.
- No page is empty. The smallest page has 30 words (the S04 cover).
- Every explicit `---pagebreak---` section starts at the top of a parsed page.

**4. Edge cases checked with a synthetic .md.**

| Input | Result |
|---|---|
| Ragged table rows (3 cells under a 2-cell header, a 1-cell row, an empty first cell) | Padded to the widest row; no text lost |
| `**bold**` inside cells | Bold runs written |
| Header row | Forced bold |
| `:---` / `---:` separators | Recognised |
| Unclosed `**` and a lone `*` | Kept literally |
| A leading `---pagebreak---` and two pagebreaks in a row | No empty page |

None of the 12 real sources actually has a ragged row, so the padding path is covered only by this test.

**5. Builds are reproducible.** Rebuilding each source into a temp dir gives parser output identical to the committed .docx files. The source SHA-256 prefixes in SOURCES.md match `sha256sum` for all 12. Docx core properties are fixed ("AI Product Studio (synthetic)", 2026-11-28) and identify no person.

**6. No personal data and no secrets.**
- Every email address is at a `.example` domain.
- Every phone number is in the Ofcom drama range `01632 960xxx`.
- There are no URLs, no titled personal names (Mr, Mrs, Cllr and so on) and no postcodes.
- There are no key, token or password strings in the sources or the builder.
- Every source carries "(fictional)" at least once.

**7. Manifest roles and loaders.** SPEC section 3 sets drafting held-out to the first pack of each sector. The demo rule in SOURCES.md is the last pack of each sector. Both are applied in SOURCES.md order:
- demo: S04, S08, S12;
- held-out: the other 9;
- drafting held-out: S01, S05, S09.

I called the loaders on the manifest:
- `eval.run.pack_names` returns 3 demo and 9 held-out packs. The two lists do not overlap, together they cover all 12 files on disk, and every listed file exists.
- `eval.run.drafting_heldout` returns S01, S05, S09. It passes its own check: 3 distinct packs, all in held-out.
- `eval.seed.find_packs` returns S04, S08, S12. The path-escape and missing-file checks pass.

**8. Amendments.** SPEC.md and EVAL.md each carry a dated amendment, made before the freeze, saying the packs are synthetic and stating the weaker-evidence caveat.

## Critical issues

None.

## Suggestions (non-blocking)

1. **Headings stranded at the bottom of a page (`build_docx.py` lines 147-149).** The 450-word break is checked before every block except tables. So when a heading is followed by a long paragraph, the break falls between them: the heading ends page N and its body starts page N+1. This happens 14 times, for example S01 page 2 "1.6 Site visits", S05 page 13 "Appendix F: Performance Management Regime", S09 page 10 "3.1 Health and safety management (weighting 4%)". The parser reports headings per page, so page N+1 holds requirement text with no heading. This is realistic enough, but it makes section attribution harder for A1-A3 than a Word-rendered document would, because Word keeps a heading with the next paragraph.
   - **Fix:** if `last == "heading"` when a break is due, put the break before the heading instead, or do not break straight after a heading.
   - **Timing:** do this only before the answer keys are written or frozen, because it moves page numbers.
2. **`--check` does not check anything (lines 187-191).** It rebuilds into a `mkdtemp()` dir, never deletes it, and only prints counts. It would be more useful if it compared parsed text and page counts against the committed `demo-data/packs/*.docx` and exited non-zero on drift. Then a source edit without a rebuild, which would leave the .md and .docx out of step, gets caught.
3. **Tables can overfill a page (line 160).** A table forces a break only past `PAGE_WORDS * 2` (900 words). Parsed pages reach 628 words (S09) and 564 words (S01), against the documented "about 450". This is harmless now. Either note it in the docstring or lower the threshold.
4. **No unit test for the builder.** It is data tooling, so this is acceptable. A 20-line test with the edge-case .md used in this review would protect the faithfulness property if the builder changes: ragged rows, bold in cells, consecutive pagebreaks, numbered lines.
5. **Any line starting with `#` becomes a heading (line 78).** For example, a line starting `#5 ...` would become a heading and lose its `#` characters. No source does this today. Requiring `#{1,3} ` (with the space) would be safer.
