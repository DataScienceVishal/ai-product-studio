# Review: T-216 slice 3 (`APP_PASSAGES` 5 -> 8)

- Branch: `p/sme-council-tender-drafting/T-216`, tip `d7b13f9`, against `origin/main`
- Reviewer: reviewer agent, 2026-11-28
- **Verdict: CHANGES.** Only docs and tests need to change. The code change is correct.

## Summary

The diff changes one constant in code (`draft.py:35`, `APP_PASSAGES = 8`). It also adds one test, updates two tests, and changes DESIGN 4.3, EVAL.md, NEXT.md and `eval/results/retrieval.json`.

What checks out:

- **The budget arithmetic is correct.** I ran the real code (`draft_reservation`, `check_reservation`, `APP_PASSAGE_CHARS=1000`, `QUESTION_CHARS=1500`, headroom 1,500) in a separate worktree at `d7b13f9`:

  | k | worst draft | typical draft (900-char hits) | re-check citing all k (3,000-char draft) |
  |---|---|---|---|
  | 5 | 12,991 | 11,344 | 17,663 |
  | 6 | 13,998 | 12,250 | 18,670 |
  | 7 | 15,005 | 13,156 | 19,677 |
  | 8 | 16,012 | 14,062 | 20,684 |

  These match DESIGN and NEXT (13.0 / 14.0 / 15.0 / 16.0k, and a 26.7k pair at k=8).
- **The reservation code matches DESIGN.** `draft_handler` (`draft.py:260`) and `/evidence` (`routes/tender.py:419`) both use `limit=APP_PASSAGES`. `Limits()` defaults to the same value, so the user still sees exactly what the drafter used (T-189 F2 still holds).
- **No value was tuned on eval labels.** The rule can never go above 8, because 8 is the retrieval depth. Recall can only rise as k rises. So any rule of the form "the largest k that fits the budget" gives 8 whatever the labels say. Recall did not choose it. `retrieval.json` `at_app_passages` now equals the pooled k=8 figures (0.7446 / 0.9643), which is consistent.
- **Targeted tests pass** on the branch: the sizing tests in `test_tender_draft.py` and `test_upload_extract_draft_and_check_fit_the_30k_trial_day`, 6 passed. I did not run the full suite, as instructed.

What blocks:

- The change has a real cost on the trial day that nobody wrote down.
- Some DESIGN figures in the section this slice edited are now false.
- Two pair-sizing tests still exercise k=5.

## Critical issues

### 1. Trial-day capacity falls from 3 questions to 2, and nothing records it

**Where:** `tests/test_tender_claimcheck.py:383-420`, `DESIGN.md:123`, the NEXT.md slice 3 status, `state/DECISIONS.md`.

**Evidence:** I ran the whole-flow test with `-s` on both trees.

- main: `reservations extract=18046 draft=11344 check=13758 ... largest pack that fits one trial day: 3 questions`
- branch: `reservations extract=18046 draft=14062 check=13758 ... largest pack that fits one trial day: 2 questions`

The test asserts `biggest >= 2`, so it now passes with no margin. DECISIONS.md (run d958, T-190) and NEXT.md (line 284) both record "at most 3 questions". The slice 3 status says nothing about the drop.

**Why it matters:** this is a trade. The drafter sees more evidence (seen recall rises from 0.626 to 0.745), but one fewer question fits a free-trial day. The Lead should make that choice knowingly. The "fixed a priori" rule checks a single draft and re-check pair. It leaves out the whole-flow-in-one-day criterion that DESIGN 4.3 itself sets. Any later growth in the prompt or passages will now fail the `>= 2` floor at once.

**Fix:**
- State the new figure (2 questions, was 3) in the DESIGN 4.3 whole-flow bullet and in the NEXT.md slice 3 status.
- Have the Lead add a DECISIONS.md entry that accepts the trade.
- Either add "the whole-flow test still fits at least 2 questions" to the written rule, or say plainly that the rule ignores it.

### 2. DESIGN 4.3 pool sentence is false: "2 to 3 pairs a day" (`DESIGN.md:124`)

**What it says:** "after two settled pairs of about 13.6k, a third draft reservation of about 22k reaches the 49k pool."

**What happens at k=8:**
- A third draft reserves 14.1k typical (16.0k worst), not 22k.
- 27.2k + 16.0k = 43.2k, which is at most 49k, so the third draft is admitted.
- After it settles (DESIGN's figure is 6k), 33.2k is used. A typical re-check (4 cited passages) reserves about 16.7k. 33.2k + 16.7k = 49.9k, which is over 49k, so the check is refused (`ai.py:726`, `ai_trial_pool_reached`).

So the pool allows **2 complete pairs a day**. A third draft can be made, but its check waits.

The 22k figure was already stale before this slice (it dates from 8 passages of 1,400 characters). But this slice rewrote the bullets around it, and the brief asked for this exact figure to be checked. It should be corrected now.

**Fix:** "the 49k trial pool allows 2 full pairs a day; a third draft (about 14 to 16k) is admitted but its check (about 17k) is refused until the next day." Check that the "10 pairs over days or 3 demo tenants" arithmetic still holds after that change.

### 3. The two older pair tests still test k=5, and an invariant stated in a code comment no longer holds

**Where:** `tests/test_tender_draft.py:240-246` and `:249-265`, `draft.py:33-34`.

**What is wrong:** both tests build `_hits(5, 900)`. The new `Limits()` would show 8 passages, but these tests only ever give it 5, so they do not exercise the change. The comment at `draft.py:33-34` says "a draft and its re-check must reserve at most 30k between them". At k=8 that is no longer true when the draft cites all 8 passages:

| hits shown | cited | draft | check | sum |
|---|---|---|---|---|
| 8 | 8 | 14,062 | 18,526 | **32,588** |
| 8 | 4 | 14,062 | 14,902 | 28,964 |
| 5 (as tested) | 4 | 11,344 | 14,902 | 26,246 |

The app is still safe, because the draft reservation is released at settle before the check reserves. DESIGN's rule (6k settled plus the check reservation) is the right model. But the comment and the first test state the stricter invariant, and the test only passes because it still uses 5 hits. `APP_PAIR_BUDGET` (`draft.py:40`) is defined but nothing in the app code reads it.

**Fix:**
- Build `_hits(dr.APP_PASSAGES, 900)` in both tests.
- Restate the comment and the first test's assertion as the admission rule: settled draft plus check reservation is at most 30k. Or keep the strict form and accept 4 cited passages as the typical case, but say which.
- Use `APP_PAIR_BUDGET` or remove it.

## Suggestions (non-blocking)

4. **DESIGN 4.3 draft bullet (line 118).** The parts listed ("4k bytes of prompt, 1.2k of question" plus 8k of passages, the 4,000 cap and 1,500 headroom) add up to 18.7k, not the 16.0k stated. The real draft system prompt is 680 bytes and the worst question is 1,500 characters. Restate the parts so they add up.
5. **DESIGN 4.3 check bullet (line 119).** "about 4, 5.6k bytes" comes from the 1,400-character era. At 1,000 characters, 4 cited passages are about 4k bytes. A check can now cite up to 8 (20.7k worst), so "6k settled plus 20k reserved is 26k" should read 26.7k worst. The whole-flow bullet's "check reserves about 14.9k" is right only for the typical case of 4 cited passages; say so.
6. **The rule assumes a 3,000-character draft, which is typical, not worst.**
   - A 1,000-word limit gives about 6,500 characters. The check citing 8 passages then reserves 24.2k. With DESIGN's 6k settled that is 30.2k, which is over the cap. With the realistic figure (about 2.7 to 4k settled) it fits.
   - A question with no word limit can produce up to 4,000 output tokens, about 16k characters. Its check then reserves 33.7k on its own: over the daily cap at any k (30.7k even at k=5).
   - This is a pre-existing gap. Consider capping the draft text sent to the check, or document that a long answer with no limit cannot be re-checked on the trial plan.
7. **The new test** uses `"x" * CHECK_SYSTEM_BYTES` (2,000) where the real `full_system(CLAIMCHECK_SPEC)` is 852 bytes. That is conservative, which is fine, but say so in the docstring. The 21.5k bound never binds at any k up to 8 (worst is 16.0k). Note that only the pair condition, and the hard cap of 8, can bind.
8. **The `test_tender_retrieval_eval.py:141` assertion** imports inside the test body and pins `== 8`. Pinning the number is fine. Move the import to the top of the file.
9. **NEXT.md** still says "Left for T-216: APP_PASSAGES 5 -> 6-8" in the slice 1 and slice 2 sections. Those are history, so that is fine, but the slice 3 status should say this item is closed.

## Evidence commands

- `git diff origin/main...origin/p/sme-council-tender-drafting/T-216`
- worktrees at `d7b13f9` and `origin/main`. From `app/backend`: `TEST_DATABASE_URL=... python3.13 -m pytest -q -o addopts="" -s tests/test_tender_claimcheck.py::test_upload_extract_draft_and_check_fit_the_30k_trial_day tests/test_tender_draft.py -k "largest or 30k or budget or reserves"`. Result: 6 passed on the branch, 5 on main, and the printed pack figures are 2 and 3.
- reservation tables from scripts that import `app.tender.draft` and `app.tender.claimcheck` (`PYTHONPATH=. python3.13`).
