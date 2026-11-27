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
