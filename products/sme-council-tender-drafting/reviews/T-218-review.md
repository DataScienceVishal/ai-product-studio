# Review: T-218 build_docx CLI guard (branch `p/sme-council-tender-drafting/T-218`, commit 6582d59)

Reviewer: reviewer agent, 2026-11-28. Diff: `git diff main...p/sme-council-tender-drafting/T-218` (3 files: build_docx.py, test_tender_build_docx.py, NEXT.md).

## Verdict: PASS

## Summary

The change does what T-218 and T-217 review S1-S3 asked:
- **S1 (CLI safety):** argparse with a mutually exclusive `--check`/`--write` group. No args, unknown args, `--only` or `--allow-frozen` without `--write`, and `--check` combined with write flags all exit 2 without writing. `--help`/`-h` exit 0. `--write` skips every pack listed in `eval/keys/FROZEN.sha256` unless `--allow-frozen` is passed. `--only` naming a frozen pack, or a pack with no source, fails before anything is written (plan first, then write).
- **S2:** the paragraph break guard is now `not only_heads` for every non-table kind, so a long paragraph no longer leaves the headings just placed alone on a page. The new test fails on the old guard, per NEXT.md, and the logic agrees.
- **S3:** `test_s08_reconciled_counts` gets the 14/5 split from the Appendix 1 table, not from hard-coded numbers, and checks it against the prose (138 cameras, 168/60 site-months, 3.3 categories 4+6+9=19, keys for all 19).
- No committed .docx layout changed, and FROZEN.sha256 still verifies.

## Evidence

```
$ cd products/sme-council-tender-drafting && python3.13 demo-data/pack-sources/build_docx.py --check
... (12 packs listed)
check: all committed .docx match their sources        rc=0

$ sha256sum -c eval/keys/FROZEN.sha256 --quiet        rc=0 (no output)

$ cd app/backend && python3.13 -m pytest -q -o addopts="" tests/test_tender_build_docx.py
40 passed in 10.64s
```

Scratch copy outside the repo (demo-data + eval/keys copied to the session scratchpad):
```
[]                       rc=2  nothing done; pass --check or --write (see --help)
[--help]                 rc=0
[--bogus]                rc=2  unrecognized arguments: --bogus
[--write --only S01]     rc=2  frozen held-out pack(s), rerun with --allow-frozen ...
[--write --only S99]     rc=2  no source for: S99
[--check --allow-frozen] rc=2  --only/--allow-frozen need --write
--write                  -> 9 "skipped (frozen ...)", S04/S08/S12 rebuilt; FROZEN.sha256 still OK; --check all match
--write --only S01 --allow-frozen -> S01 rewritten; sha256sum reports S01 FAILED (expected: the flag is explicit); --check still all match
```

## Critical issues

None.

## Suggestions (non-blocking)

1. **The frozen list fails open.** `frozen_names()` (build_docx.py, around line 272) returns an empty set when FROZEN.sha256 is missing. It also matches only text-mode lines (`hash  path`). A binary-mode line (`hash *demo-data/packs/...`) is silently ignored. I confirmed this in scratch: rewriting the paths with a `*` prefix gives `frozen with * prefix: 0`. In both cases `--write` would rewrite all 12 packs with no warning. Fix: strip a leading `*` from the path, and make `--write` refuse (exit 2) when the list is missing or has no .docx entries, unless `--allow-frozen` is passed. Add a test for each case. Low risk today because the file is committed in text mode, but this is the guard T-218 exists to add.
2. **A test can damage the repo if the guard regresses.** `test_cli_refuses_without_writing` runs the real builder against the real `demo-data/packs/` and only detects writes afterwards through mtimes. A regression would rewrite the frozen packs during the test run. Copy `build_docx.py` and the sources into `tmp_path/pack-sources/` (OUT is resolved relative to the script) and run it there, or at least point FROZEN_LIST and OUT at a tmp copy.
3. **A heading can still sit alone at the foot of a page (pre-existing, outside S2).** With 300 words on a page, then `## Method` and a 460-word paragraph, the heading lands at the foot of page 1 and the paragraph starts page 2. The heading lookahead counts only `min(next, 80)` words, but the builder never splits a paragraph across pages. Reproduced in scratch: page 0 = `[Normal, Heading 2 'Method']`, page 1 = `[Normal]`. No committed pack is affected (`--check` passes). If it matters for page references, use the next block's full word count when it is a para, bullet or number that cannot fit in what is left of the page.
4. **Minor:** `main()` catches `SystemExit` from argparse and returns `e.code`. That works for these flags, but argparse can raise with a string code. `int(e.code or 0)` would then raise ValueError. Low impact.
