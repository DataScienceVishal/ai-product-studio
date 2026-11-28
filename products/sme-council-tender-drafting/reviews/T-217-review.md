# T-217 review: S08 counts reconciled, builder heading/table fix, test and EVAL nits

Branch `p/sme-council-tender-drafting/T-217`, commit 32ff310, against `origin/main` (merge base d6b9596). Reviewed in a separate worktree.

**Verdict: PASS**

## Evidence

- Full backend suite on the exact branch tree, fresh db `t217_rv`: `1303 passed, 1 skipped in 261.12s` (expected 1303 passed, 1 skipped).
- `python3.13 demo-data/pack-sources/build_docx.py --check`: `check: all committed .docx match their sources`, exit 0, all 12 packs. Working tree clean afterwards.
- `sha256sum -c eval/keys/FROZEN.sha256` (34 entries): all OK. S08 is a demo pack and is not in FROZEN.
- `git diff --name-only origin/main...HEAD -- eval/`: empty. `eval/keys/retrieval_labels.json` is untouched. Under `demo-data/packs/` only `S08-security-trust-cctv-keyholding.docx` changed.
- SOURCES.md hash `66b37297b90162e7` equals the first 16 hex characters of sha256 of the S08 `.md` source (the column is the source hash). The old hash `f13e0bd3...` survives only in NEXT.md's historical T-212 section, which is fine.

## S08 internal consistency (whole source checked)

| Fact | Where | Value |
|---|---|---|
| Alarm sites | 3.2, 3.3 ("all 19 sites"), Lot 3 (19), Appendix 1 intro, Appendix 1 rows 3+1+1+5+4+5 | 19 |
| CCTV sites | 3.2 "14 sites with 138 cameras", Lot 1 "14 CCTV sites", Appendix 1 intro, Appendix 1 rows with cameras > 0 (3+1+1+5+4) | 14 |
| Cameras | 3.2, Appendix 1 74+22+12+10+20 | 138 |
| Alarm-only sites | Lot 2, Appendix 1 "Other sites 5 0 Alarm only" | 5 (19 - 14) |
| Site-months | Lot 1 14x12 = 168, Lot 2 5x12 = 60 | correct |
| 3.3 response categories | 4 (3 leisure + market) + 6 (business centre + 5 units) + 9 (4 halls + 5 other) | 19 |
| Priority 1 sites | 3.2 "market and three leisure centres" = 3.3 Category 1 | 4 |

No stale "11 CCTV", "132", "96" or "8 alarm-only" remains anywhere outside reviews/. None of the changed sentences appears in `retrieval_labels.json` (the S08 labels are question texts Q1-Q7, none of which changed).

## Builder fix (build_docx.py:139-200) against the T-212 S1 latent issue

T-212 S1 said that a table over 900 words stranded its heading alone on a page, and that a run of headings before a table of about 890 or more words split the same way. The fix tracks `heads_on_page`, the words of the headings placed at the top of the current page. It (a) skips the heading break when the page holds only those headings, and (b) skips the table-forced break when the page holds only those headings. I traced the edge cases:

- A fresh page (`on_page == 0 == heads_on_page`) gives `only_heads` True, so a paragraph placed there resets `heads_on_page` to 0 and the next block sees `only_heads` False. Correct.
- `page_break()` resets `heads_on_page`. `only_heads` is recomputed after a possible break, so a heading that broke onto a new page starts a fresh heading run. Correct.
- A heading placed after body text gets `heads_on_page = 0` (because `only_heads` is False), so later blocks never treat that page as heading-only. Correct.

Tests: `test_oversize_table_does_not_strand_its_heading_alone` covers both the single heading and the two-heading run and asserts exactly 2 pages, with page 2 starting with a heading and ending with the table. `test_oversize_table_at_the_top_of_a_page_keeps_one_page` checks that nothing breaks before the first block. They test behaviour (rendered page contents), not internals. `--check` proves no committed pack changed layout.

Retrieval test bound: `n_docs = len(evidence docs)` replaces the magic 32. Fine.

EVAL.md amendment: it is dated, labelled documentation-only, and defines `all_primaries_hit_rate` (every primary in top k, so it is never above the first-primary rate) and `labels_sha256` (sha256 of the exact bytes of `eval/keys/retrieval_labels.json` that were scored). It is clear and does not change any bar.

## Critical issues

None.

## Suggestions (non-blocking)

**S1. `build_docx.py --help` (or any argument other than `--check`) rewrites all 12 packs, frozen held-out packs included** (build_docx.py:264-275). Confirmed: `main()` only tests `"--check" in argv`, and everything else falls through to the rebuild loop. I ran `--help` in a scratch copy of the product: it wrote into `demo-data/packs/`, and afterwards `sha256sum -c eval/keys/FROZEN.sha256` reported 3 FAILED after only 2 to 3 packs had been written (the run was cut short by a closed pipe). Python-docx timestamps its zip members, so every rewrite changes the bytes even when the text is the same. This predates T-217 and nothing harmful is committed. `git checkout` recovers, and the frozen-hash check would catch a bad commit. Fix (trivial, about 4 lines): reject unknown arguments, print the module docstring on `-h`/`--help`, and require an explicit `--write` (or `--only S08`) to rebuild. Ideally the default rebuild should skip held-out packs unless asked. Do this in the next builder touch.

**S2. Paragraph overflow can still strand headings.** If a page holds only headings and the next paragraph alone exceeds `PAGE_WORDS - heads`, the non-heading branch still breaks, leaving the headings alone. Latent only: `--check` shows no committed pack lays out differently, but the largest blank-line-separated block in the sources is about 450 words (PAGE_WORDS), so a future long paragraph under a heading could hit it. A one-line guard (`not only_heads` for paragraphs too) would close it.

**S3. Pin the reconciled S08 numbers in a test.** `test_s08_appendix_1_lists_19_sites` checks 19 sites and 138 cameras but not 14 CCTV sites, 168 or 60 site-months, or the 3.3 category total. A small extension would stop the next prose edit from drifting again (this is the second S08 count fix).
