# Review: p/sme-council-tender-drafting/T-198 (head 57c75c6)

**Verdict: PASS** (no blockers; should-fix items 1-2 can go on the next slice's board task)

## Summary
Fixes for the T-188 leftovers: runner `FAILURE_HOOKS` on `attempts_exhausted`, migration 0017 unique (tenant_id, pack_id, seq) with a duplicate renumber, pack row lock in `add_requirement` and the extract write, F10 source_page clamp + `page_out_of_range` flag, F5 limit window on the raw text plus "sides of A4" page limits, duplicate import removed, and the F9 decision (one extract task per pack) recorded in NEXT.md.

## Evidence
- `pytest tests/test_tender_extract.py`: **27 passed** (reviewer run, real Postgres). Builder reports full suite 976 passed, 1 skipped.
- **0017 renumber SQL run on a scratch DB with real duplicates** (`t198_scratch`, dropped after). Input: pack A seqs {1,1,1,2,2,5}, pack B {1,2}, tenant-2 pack C {3,3}. Output: A {1,2,5,6,7,8}, B {1,2} unchanged, C {3,4}. `UPDATE 4`, and the unique constraint then applied cleanly. Reasoning agrees: every moved row gets `max(seq) + rn` with `rn` distinct within the pack and `> 0`, every row that stays has `seq <= max`, and the constraint is created after the UPDATE, so there is no conflict during the update. Partitions include tenant_id, so nothing crosses tenants.
- Lock ordering: `add_requirement` locks the pack, then inserts. The extract write deletes model proposals, then locks the pack, inserts, and updates the pack. The hooks run a single UPDATE on the pack in their own session, after `claim_next` has committed, so no task-row lock is held. The draft save takes FOR SHARE on the pack and touches no requirement rows. I found no cycle: `add_requirement` never waits on a requirement row while holding the pack lock, because its unique key is only contended by a holder of the same pack lock. No deadlock path.

## Findings

1. **should-fix**: `app/tender/extract.py:232-239`. The pack lock is taken *after* the DELETE and after `existing` is read. Under READ COMMITTED, a user row that `add_requirement` commits between the `existing` SELECT and the lock is missing from the dedupe list, so extraction can add a duplicate proposal next to it. seq stays correct, because `base` is read after the lock. Fix: take the pack FOR UPDATE as the first statement of that transaction. That also gives every writer the same pack-then-requirements order.
2. **should-fix**: `app/tender/extract.py:99-111` (F5). The window now starts at the quote. The old code looked 200 characters before it; the new code doesn't look back at all. A UK-style heading such as `Q3 Social Value (max 500 words, 10%)` followed by the question body on the next line, where the model's quote is the body, now yields `stated=None`, so a wrong `word_limit` goes unflagged. That is a false-negative regression on a safety flag. Fix: start the window at the previous `_NEXT_QUESTION` boundary before the quote (or at the start of the page), not at `m.start()`. Add a test with the limit in the heading.
3. **nit**: `app/tender/draft.py:275-284`. No code ever sets pack status `checking` (grep: only `DRAFT_PACK_STATES` and this hook mention it). The draft hook is dead until a check phase exists, and its test sets the state by hand. Keep it, but say so in the docstring, or drop it until the check phase lands.
4. **nit**: `app/tender/extract.py:_NEXT_QUESTION`. A numbered sub-list inside the question's own guidance (`\n1. Your approach\n2. ...`) ends the window early, so a limit stated after the list is missed (no flag, not a false flag). `_PAGE_LIMIT` also misses "2 A4 pages" and "two sides". Worth a fixture from a real ITT.
5. **nit**: `migrations/.../0017`. Which duplicate keeps its seq depends on `ORDER BY id`, and ids are random UUIDs. Renumbered rows move to the end of the pack, so the user-visible order can change. That's acceptable for demo data, but `ORDER BY created_at, id` would keep the order closer to how the rows were written.
6. **nit**: `app/tender/extract.py:249-251`. The clamp is right (empty `pages` is guarded, negatives go to the first page). Dedupe in `merge_items` and against `existing` still uses the unclamped page. That's harmless today and worth a one-line comment.

## Security / tenancy
Every new query filters on tenant_id (the hooks, the locks, the migration partitions). No new endpoints and no new AI calls, so no cost change.
