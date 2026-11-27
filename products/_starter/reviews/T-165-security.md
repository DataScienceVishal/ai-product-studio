# T-165 security and privacy pass: product starter changes since 1cb2529

- Scope: `git diff 1cb2529..HEAD -- products/_starter` (HEAD 584fca3). This covers T-162 (QA fixes: exact reported-model
  price match, `_clean_model`, chat `refusal`), T-163 (`ai_guard_trips` persisted trip with fail-closed reads,
  migration 0008, `TripStore`, route passes its session) and T-164 (`_clean_reason` for the `finish_reason` log field,
  pinning tests). Code reviewed: `backend/app/ai.py`, `backend/app/aicost.py`, `backend/app/models.py`,
  `backend/app/main.py`, `backend/app/routes/notes.py`, `backend/migrations/versions/20261126_0008_ai_guard_trips.py`,
  `backend/tests/test_ai.py`, and `infra/db-grants.sql` for the privileges on the new table.
- T-161 findings are not repeated here. Their status: M1 is fixed by T-163, L1 by T-162/T-163 (`deployment_in_table`),
  and L2 by T-162 (`_clean_model`). I1 and I2 are unchanged and out of scope.
- Reviewer: security agent, 2026-11-27. I did not modify any code. Probes ran from the scratchpad and were not added
  to the repo.

## Verdict: PASS

There are 0 high, 0 medium, 1 low and 3 nits. Nothing is exposed right now: the starter is not deployed and the deploy
default is still `ai_provider=fake`. Nobody needs to ping Vishal.

Suggested board task for L1: "T-xx starter: retry a failed model-guard trip write instead of dropping it (T-165 L1)".

## Findings

### L1 (low, money): if the trip write fails it is never retried, so every fresh process pays for one more expensive call
- Where: `backend/app/ai.py:399-404` (`record` failure is logged and dropped) and `:365` (`check_persisted_trip`
  returns early once `self.disabled` is True, so nothing ever writes again).
- Failure scenario: Azure starts reporting a dearer model, possibly because the deployment was repointed. The call
  that trips the guard tries to `INSERT` the row, but the database is slow or failing over at that moment, or the pool
  times out under the same load that is driving AI traffic. The row is never written. This process stays off, but:
  - Every other replica still treats the AI as on.
  - Every cold start does too, and the app scales to zero (`minReplicas: 0`).
  - Each of them makes one more call at the expensive model's price, trips, and tries the write again.

  This is the T-161 M1 failure mode again, reduced to about one expensive call (about $1.10 for gpt-5.4-pro) per
  process start until a write finally succeeds. Nothing else warns the operator apart from one log line.
- Evidence (probe `test_p1_lost_trip_write_is_never_retried`, first `record` raises):
  - Process A: `[200, 503, 503]`, 1 model call, **1 record attempt**. The two later refusals did not retry the write.
  - Fresh process B: `[200, 503]`, **1 more model call** (the lost trip). Its own trip then saves the row.
  - Fresh process C: `503`, 0 calls.
- Why it is only low: it needs both a dearer or unknown reported model and a database write failure at exactly the
  moment of the trip, and the global daily token cap still bounds the total.
- Fix: keep a `trip_unsaved` flag. While it is set, `ensure_ai_enabled` / `check_persisted_trip` retries
  `record(...)` even when `disabled` is True. Rate-limit the retries, for example once every 30 s, and run them on the
  caller's session or a short own session. Clear the flag on success. Add a test where the first write fails and the
  second request in the same process writes the row, so a fresh process then refuses with zero calls.
  Optionally, report `ai: "disabled"` on `/api/health` so a smoke test can see a trip.

### N1 (nit): clearing a trip by hand needs a restart too, but the log line does not say so
- Where: `backend/app/ai.py:376-377`, and the model docstring at `models.py:114-117`.
- Scenario: an operator follows the message "or delete the row in ai_guard_trips". Replicas that have already latched
  `disabled` in memory stay off until they restart, so it looks as if the fix did not work. This is fail-closed, so
  there is no security impact.
- Fix: add "and restart the app" to the message and the docstring.

### N2 (nit): `_clean_model` allows any printable Unicode, not the allowlist T-161 L2 suggested
- Where: `backend/app/ai.py:59`.
- Scenario: an upstream (an OpenAI-compatible proxy, not Azure) reports `gpt-5-mіni` with a Cyrillic `і`. That
  string is stored in `ai_usage.model` and logged, so a later spend report grouped by model could be confused by the
  look-alike name.
- Money is not affected, because the price check uses the raw value, finds it unknown, and fails closed (it trips).
  The log cannot be forged: the probe shows that NUL, CR/LF, ESC, U+202E, U+200B and U+3000 are all stripped, the
  result is at most 80 characters, and `pending`/`abandoned` in any case or padding become `unknown`.
- Fix (optional): use `^[A-Za-z0-9._:-]{1,80}$` and map anything else to `unknown`.

### N3 (nit): the fingerprint is an unsalted SHA-256 of endpoint, deployment and price
- Where: `backend/app/ai.py:356`.
- Scenario: someone who can already read the database could confirm a guessed endpoint URL and deployment name
  against the hash. Neither is a credential (no key or token is in the basis), and that reader already has more
  sensitive data. Information only. No change is needed. If you want it hidden anyway, use an HMAC keyed with an
  existing app secret.

## Checked and fine

- **No fail-open in the cost/model guard.**
  - A read error raises 503 `ai_budget_reached` with the neutral text "The AI is unavailable right now. Everything else
    still works." It does not latch (`ai.py:366-373`).
  - The route checks before `reserve`, so a refusal leaves no reservation. `complete()` checks again
    (`ai.py:407`) after `reserve` has committed and released the request connection. If that second read fails, the
    route's `except Exception` settles the reservation as `failed`.
  - `create_app` attaches the store to any provider that has `attach_trip_store`. `build_provider` is only called
    from `main.py`, so no other entry point skips it.
  - The price match is exact after one ASCII date suffix is removed. Odd names (`gpt-5-mini-pro`, double dates, NUL,
    Unicode digits or case tricks) become unknown and trip.
  - `price_explicit` now uses the same exact-name rule as `resolve_price`, so an explicit price can no longer wave
    unknown models through for a deployment the table knows.
  - Chat `refusal` is treated as no answer. Its tokens are billed and its text is neither returned nor logged.
- **Logs.**
  - Read and write failures log only `type(exc).__name__`, never the exception text, so no connection string or host
    appears.
  - `finish_reason` passes through `_clean_reason`: printable only and at most 40 characters. The probe shows
    `"stop\nX"` becomes `stopX` and ESC sequences are stripped.
  - The model name is cleaned before it is logged or stored. No prompt, answer or key is logged. The logs are JSON in
    any case.
- **Tenant isolation.** `ai_guard_trips` is a global, operator-level table. It has no tenant column and holds no tenant,
  prompt or answer data. No route reads it or returns it. A tenant cannot write it: the row is only written when the
  upstream `model` field trips the guard, and tenant input cannot set that field. The trip is fleet-wide by design and
  fails closed.
- **Unbounded writes and DoS.**
  - There is at most one row per AI configuration: `INSERT ... ON CONFLICT DO NOTHING` on the primary key, written
    only on a trip, which happens once per process.
  - The cost per request is up to two primary-key reads until the process latches. The route's read reuses the request
    session, so there is no nested checkout. This is pinned by
    `test_fresh_process_on_a_tiny_pool_reads_the_persisted_trip` and
    `test_route_trip_check_uses_the_request_session_not_a_second_connection`.
  - `complete()`'s own read runs inside the `AISlots` bound with no request connection held.
  - A broken database makes every AI request log one error line, which is bounded by the per-tenant AI rate limit.
- **Migration 0008** only does `CREATE TABLE`: it locks no existing table, adds no backfill and no column default on a
  large table. `tripped_at` has `server_default now()`, which matches the model (`alembic check` is clean). Downgrade
  is `DROP TABLE`. The table holds only a re-creatable trip marker, so losing it on downgrade is acceptable.
  `test_migrations` (upgrade, check, downgrade) passes.
- **Privileges.** The app role gets SELECT/INSERT/UPDATE/DELETE on the new table through `ALTER DEFAULT PRIVILEGES`
  (`infra/db-grants.sql:19`). It cannot change the schema. That is least privilege for what the code needs.
- **Error messages.** None of the refusals reveal the model, price, deployment, endpoint or exception.
- **Secrets scan** of the added lines in the diff, for Stripe `sk_live`/`sk_test`, `whsec_`, `AKIA`, GitHub tokens, PEM
  private keys, `AccountKey=`, Slack, Telegram bot tokens, JWTs and literal api keys: **no matches**.
- **Dependencies.** `requirements*.txt` and the frontend lockfile did not change in this scope, so T-100's audit
  results still stand.
- **Privacy.** No new personal data is collected. The new table stores no personal data.

## Tests run (local Postgres 16, Python 3.12 venv in the scratchpad, HEAD 584fca3)

- `cd products/_starter/backend && python -m pytest -o addopts="" -q -p no:cacheprovider tests/test_ai.py tests/test_migrations.py`
  -> **178 passed, 1 warning** (16.7 s).
- Full suite, `python -m pytest -o addopts="" -q -p no:cacheprovider` -> **723 passed, 1 skipped, 1 warning** (99.3 s).
- Probes, run with `-p tests.conftest` from the scratchpad: `test_p1_lost_trip_write_is_never_retried` (results under
  L1) and `test_p2_clean_model_edges` (all assertions held; results under N2 and Logs). **2 passed.**
