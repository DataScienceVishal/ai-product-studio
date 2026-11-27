# Review: T-191 (S7 review screens, coverage and sign-off)

Branch `p/sme-council-tender-drafting/T-191` at c033f9a, diff against origin/main. Reviewer run 2026-11-27.

## Verdict: CHANGES (one must-fix, small)

## Evidence
- Backend full suite (Postgres, db `t191r`): **1155 passed, 1 skipped** in 305 s (includes `tests/test_tender_review.py`, `tests/test_spa.py`).
- Frontend: `npx vitest run` **228 passed**; `npx tsc -b` clean.
- `grep dangerouslySetInnerHTML|innerHTML|£|price` on `pages/tender.tsx`: no hits. Tender text, passages and claim spans render as React text nodes; `AnswerText` has a test that markup is not rendered.

## What is right
- Tenant isolation: `GET /packs/{id}`, `/coverage`, `/signoff` use `get_scoped`; `/evidence/passages` filters `EvidenceItem.tenant_id` and joins `SourceDocument` on tenant and id; ids parsed as ints, capped at 100, 422 on junk. Cross-tenant test covers all four plus `/check`; passages test shows another tenant gets `[]`.
- Sign-off: pack row FOR UPDATE with `populate_existing`, tick + current statement version required (422), 409 unless `ready`, gate re-run with the would-be sign-off; on block nothing is stored and the status is untouched (tests for stale `ready` with blocked claims and with deleted evidence).
- `queue_check` FOR UPDATE; `pack_checked` refuses `ready` on evidence_removed etc., tested by deleting evidence mid-check (T-201 items 5, 8).
- Polling: timeout chain, one request in flight, 3 s, doubling to 15 s on error, 200-tick cap, stops when not busy and on unmount; tested with fake timers.
- CLIENT_ROUTES mirrored; deep links with `?id=` return 200 for GET and HEAD, and path-style ids 404.

## Critical issues (must fix)
1. **Edit-after-sign-off race leaves a pack stuck forever** - `app/backend/app/routes/tender.py` `edit_draft` (lines ~430-444). It reads `pack.status` via `_question` without a lock, so an edit that passed the check can commit a new draft after `sign_off` commits. `reopen_pack` only moves `ready -> drafting`, so the pack stays `signed` with a digest mismatch. The gate fails closed (no leak), but there is no way out: edit, redraft, check and sign-off all refuse a `signed` pack, so the bid is dead until S8 ships a void path. Not acceptable to carry: the fix is one statement and the draft worker (`tender/draft.py` ~261) already does it. **Fix:** in `edit_draft`, before the status check, re-read the pack with `.with_for_update(read=True)` (FOR SHARE, as the worker does) plus `populate_existing`, and test that a sign-off committed between the read and the save makes the edit 409 (or simulate by setting `signed` after `_question`).

## Suggestions (not blocking)
- Same unlocked-status-then-lock order on the requirement edit/add routes (`tender.py` ~288 and ~307: status checked before the FOR UPDATE at ~291). Pre-existing; fix alongside item 1 by locking first.
- Coverage page copy says "Any change to an answer or the checklist means signing off again", but edits are locked after sign-off in this slice. Reword until S8.
- `coverage()` runs two queries per requirement (latest draft, claim counts). Bounded by checklist size, fine now; one windowed query later.
- `usePoll` keeps polling on 401/404 (backs off to 15 s, stops at 200 ticks, about 50 min). Consider stopping on 4xx.
- `usePoll` does not restart when `packId` changes while active; harmless today since each page mounts per id.

---

# Re-review at dbc52b1: PASS

## Evidence
- `tests/test_tender_review.py`, `test_spa.py`, `test_tender_draft.py`, `test_tender_extract.py`: **223 passed, 1 skipped**. Frontend vitest **229 passed** (one new); `tsc -b` clean.
- **The race test is real.** With the new `_lock_pack` line removed from `edit_draft`, `test_an_edit_racing_a_sign_off_waits_for_it_and_is_refused` **fails**; with the line back, it passes. It holds the pack row in a second session, checks that the edit thread is blocked, commits `signed`, then checks for a 409 `pack_locked` and that no new draft version was written.

## Must-fix 1: fixed
- `edit_draft` now re-reads the pack with `_lock_pack` (FOR UPDATE plus populate_existing) before the status check.
- **FOR UPDATE rather than FOR SHARE: the reasoning is correct.** The edit routes then UPDATE the same row (`reopen_pack`, or the add/patch writes). If two transactions each hold FOR SHARE and both try to upgrade to a row write, they deadlock, and Postgres aborts one with 40P01. FOR UPDATE queues them one after another instead. The draft worker's FOR SHARE is safe against these routes: a FOR UPDATE edit waits for it, and a single sharer can upgrade.
- Residual, not blocking: two draft workers on the same pack could both take FOR SHARE and then both hit `reopen_pack`. That depends on whether pack-wide and per-requirement draft tasks can run at the same time. Worth a look in S8, or switch the worker to FOR UPDATE.

## Suggestions: done
- `add_requirement` and `edit_requirement` now lock before the status check (the earlier lock-after-check order is gone). A test confirms both return 409 after sign-off.
- `usePoll` stops on any `ApiError` 4xx; other errors still back off. Tested with a 404 (one call in 60 s). The test name also says "keeps backing off on a network error", but only the 4xx path is checked there. The earlier backoff test covers the other path.
- The coverage copy now says the answers and checklist are locked.

## Verdict: PASS
