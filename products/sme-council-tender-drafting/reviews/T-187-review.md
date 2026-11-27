# Review: T-187 (S3, AI layer and job runner)

Branch `p/sme-council-tender-drafting/T-187` at 4008c19, diff against origin/main. Reviewer run, 2026-11-27.

**Verdict: CHANGES** (two small, required fixes; everything else meets the bar)

## Tests (run by the reviewer)

`cd app/backend && TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python -m pytest -q -o addopts=""`
(Python 3.11 venv, Postgres 16): **921 passed, 1 skipped** in 168 s. Matches NEXT.md (898 + 23 new in `tests/test_tender_ai.py`).

Two reviewer probe tests (written, run, then deleted; not committed) confirmed C1 and C2 below: both passed, meaning
the bug exists.

## Summary

The bar is mostly met. The cache key is computed before the nonce (R1), and the cache is looked up per tenant
(PK `(tenant_id, key)`, and the query filters on both). The nonce is 16 random hex characters, re-drawn if it appears
in the payload, and every value sits inside a DATA block. The budget port works: `AppBudget` passes the same caps as the
starter route, the double-cap retry is harness-only, and a truncated answer in the app gives `ai_truncated`. The three
adapter changes, with `build_worker_provider` at 180 s, are tested at the HTTP layer. `ScriptedFakeAI` refuses any
`eval` path and its recorded-key lookup is safe from path traversal. `ai_access` is in place. The purge deletes by age
only. Two problems remain. The runner has no fencing token, so a worker whose lease was taken over can still write. One
failure path in `run_task` leaks a budget reservation.

## Critical issues

**C1. No fencing after a lease takeover: a superseded worker overwrites the new owner's task.**
`app/tender/runner.py:55-58` (`extend_lease`) and `:62-64` (`_finish`) match on `tenant_id, id` (and `status='running'`)
only. Worker A's lease can expire while A is still alive: a stalled replica, a DB or network pause, or a handler that
makes several calls between heartbeats. Worker B then takes the task over with `attempts=2`. A's late `_finish`
overwrites B's status and error code and adds A's tokens. A's `heartbeat()` also keeps extending B's lease. Probe:
claim, take over at `now+1 min`, call `_finish` with the old task, and the row shows the old worker's error code. Once
S4 to S6 handlers write drafts and claims, this becomes double writes from two owners.
*Fix:* use `attempts` as the fencing token. Add `AITask.attempts == task.attempts` (and `status == 'running'` in
`_finish`) to both UPDATEs. In `_finish`, check `rowcount`. If it is 0, log "lease lost" and drop the result. Give
handlers a way to see that the lease was lost: `heartbeat()` returns False or raises `LeaseLost`, and handlers check it
before writing. Add a test: take over the task, then the old `_finish` and `extend_lease` are no-ops.

**C2. A reservation leaks when `before_call` raises.**
`app/tender/llm.py:188-190`. `budget.hold()` commits a pending `ai_usage` row, then `before_call()` runs **outside**
the `try`. In the runner, `before_call` is `extend_lease`, a DB write. If it raises (DB blip, pool timeout), the
reservation stays pending. It counts against the tenant's daily cap and in-flight limit until the 15-minute stale sweep.
On a 30k trial cap that blocks the tenant's one daily redraft. Probe: `before_call` raises with `AppBudget`, and the
`ai_usage` row stays pending. The brief asked for no leaked reservations on any failure path.
*Fix:* call `before_call()` before `budget.hold()` (preferred: there is nothing to settle if the heartbeat fails), or
move it inside the `try`, whose `except Exception` already settles. Add a test with `MemBudget`: `before_call` raises,
and every hold has a matching settle.

## Suggestions (not blocking)

1. `tests/test_tender_ai.py:360` `test_skip_locked_lets_two_workers_take_different_tasks` claims one task after the
   other, so the second claim skips task A because of its live lease, not because of SKIP LOCKED. Add a real test: hold
   `SELECT ... FOR UPDATE` on task A in an open session, then `claim_next` from another session returns task B without
   blocking.
2. `runner.py:83,86`: a failed task records 0 tokens on `ai_tasks` even when `run_task` billed calls (they are in
   `ai_usage`, so caps are right, but the task row under-reports). Carry the tokens on `TaskFailed` / `AIUnavailable`
   if S8 shows per-task cost.
3. `llm.py:37` comment says the injection rule "is part of the key". It is not: `canonical_key` hashes `spec.system`
   without `INJECTION_RULE`. Either add the rule to the key, or fix the comment. If the rule's wording changes, the
   cache should change with it, so adding it to the key is preferred.
4. `llm.py:213` repair text puts Pydantic `loc` parts outside the DATA block. With `list[dict]` fields such as
   `ExtractOutput.items`, the loc stays index-based. A `dict[str, ...]` field would echo model-chosen keys into the
   instruction area, and model output can be steered by injected document text. Limit `loc` parts to `[A-Za-z0-9_]{1,40}`
   or ints. The repair message also does not show the model its previous answer. That is acceptable for a stateless
   re-ask, but say so in a comment.
5. `reserve()`'s in-flight window is 2 minutes (`ai.py:699`), while worker calls may run 180 s. A long call stops
   counting toward `ai_calls_per_tenant_at_once` before it ends. This is harmless at 2 threads, but note it for S4.
6. Decision 3 ("handlers must build their provider with `build_worker_provider`") is a convention only. Have `Runner`
   build the worker provider once and pass it to handlers, so a handler cannot use the 20 s request provider by mistake.
7. `ScriptedFakeAI.recorded_answer` lets a corrupt fixture's `JSONDecodeError` escape, and the runner then records
   `internal`. Map it to `TaskFailed("ai_invalid_output")`, as is already done for a schema-invalid recording.

## Builder's design decisions (NEXT.md)

NEXT.md lists three decisions, not five. They are judged here, together with the two choices recorded under Done that
change behaviour.
1. **Recordings looked up by `run_task` through `provider.recorded_answer(task, key)`:** agreed. `complete()` only sees
   nonce-wrapped text, so this is the only way to keep R1. Recorded answers are free and bypass the budget, which is
   correct.
2. **Threads off by default (`AI_WORKER_THREADS=0`), lease 600 s:** agreed. While `HANDLERS` is empty, turning threads
   on would only fail tasks as `no_handler`. S4 must set 2 in the deployment.
3. **Handlers build their own worker provider:** acceptable, but enforce it (suggestion 6).
4. **Truncation fails in the app; double cap only with `allow_double_cap`:** correct per R3. DESIGN 4.3's older
   truncation bullet is overridden by section 13 R3.
5. **`ScriptedFakeAI.cacheable = False`:** agreed. It keeps canned output out of the demo cache.

## Checked and fine

- R1 ordering and test: the second call hits at 0 tokens, with one provider call and one hold. Reversed dict order gives
  the same key. Every canonical part changes the key.
- Hold and settle: settled on `AIUnavailable` (billed tokens, `:failed`), on any other exception (0, `:failed`), on
  success before validation (so a repair retry never double-holds), and on truncation. A budget refusal stops before the
  provider.
- The fake never reads `eval/keys`: the constructor refuses any resolved path with an `eval` part, and the test spies
  `open`, `io.open` and `Path.read_text`.
- Tenant isolation: `ai_cache` read and write are by `(tenant_id, key)`; runner UPDATEs filter `tenant_id`.
- Purge: `DELETE FROM ai_cache WHERE created_at < now - 90d`, parameterised, age only; other tables untouched (tested).
- Claim: `FOR UPDATE SKIP LOCKED LIMIT 1` with a commit before the call; no transaction open across a model call
  (rule 11). `attempts >= 2` gives `attempts_exhausted` and does not loop.
- Adapter: strict `text.format` and chat `response_format`; the schema name is sanitised; `effort` is validated; the
  worker timeout is applied per attempt (tested at 180 s against the 20 s request path).

---

# Re-review at 459d453 (builder's fixes)

**Verdict: PASS**, with one item (N1) that must be fixed before any slice turns the runner on.

**Tests (rerun by the reviewer):** 928 passed, 1 skipped in 186 s. That is 921 plus 7 new tests.

## C1 and C2: fixed

- **C1 (fencing): fixed.** `runner.py` `_owned()` matches on `tenant_id`, `id`, `attempts` and `status='running'`.
  `extend_lease` and `_finish` both use it and check `rowcount`. A superseded `heartbeat()` raises `LeaseLost`.
  `run_one` catches `LeaseLost` and writes nothing. Its `AppError` and `Exception` paths go through the fenced
  `_finish`, so they are safe too. Two tests cover it: the old worker's `extend_lease` and `_finish` do nothing, and
  `run_one` drops a result after a takeover in the middle of a run.
- **C2 (leaked reservation): fixed.** `before_call()` now runs before `budget.hold()`, so a lost lease or a database
  error leaves no hold. The test checks `holds == []` and that the provider was never called. The heartbeat on the
  repair and double-cap rounds also runs after the previous round settled, so no hold is pending then either.
- **Suggestions 5, 6, 8 and 9: done and tested.** The injection rule is now in the key. Repair locations are
  allow-listed (`d.?`). The worker provider is passed to handlers. A corrupt fixture gives `ai_invalid_output`.
  Suggestions 3, 4 and 7 are carried in NEXT.md.

## New finding

**N1 (blocker for S4, or whichever slice sets `AI_WORKER_THREADS > 0`): the worker provider has no trip store.**
At `app/main.py:183`, `build_worker_provider(settings)` is built in `lifespan`, but `attach_trip_store(TripStore(...))`
is only applied to `app.state.ai` (`main.py:203-205`). The worker's `AzureOpenAI` therefore:
- skips `check_persisted_trip` (`ai.py:395` returns early when there is no store), so it ignores a model-guard trip
  that the request path or another replica has saved;
- does not save its own trip, so every restart or scale-from-zero allows another call to the wrong, expensive model.

This undoes T-163 for the job runner. It cannot happen today: threads are off and `HANDLERS` is empty. That is why it
does not block this merge.
*Fix:* in `lifespan`, call `attach_trip_store(TripStore(app.state.db.sessions))` on the worker provider when it has
the method. Add a test that the Runner's provider has a trip store when `ai_provider=azure`.

## Nits

- `runner.py:29-31`: `class LeaseLost` sits between the Handler comment and `HANDLERS`. Move it above the comment.
- `main.py:184`: `ai or build_worker_provider(...)` makes an injected test provider serve as the worker provider. That
  is fine for tests, but add a comment saying so.
