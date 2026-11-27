# T-163 review: persist the model-guard trip (T-161 M1), explicit price scope (T-161 L1)

Branch `p/_starter/T-163`, head bf7d109, diff `cdfeaba..HEAD` (9 files, +318/-18). Reviewer: reviewer agent, 2026-11-27.

## Verdict: CHANGES

One blocking issue. The design is right and the tests are mostly strong, but the new route-level trip check takes a
second pooled connection while the request session still holds one, so normal concurrent load can exhaust the pool and
turn every AI call into a 10-second wait followed by a 503. I reproduced this.

## Evidence

- Full backend suite: `pytest -q -p no:cacheprovider` -> **719 passed, 1 skipped** (count read with `-o addopts=""`, because
  `addopts = "-q"` plus `-q` hides the summary line). Matches the builder's figure (712 + 7 new).
- Migration 0008: `test_migrations` upgrades to head, runs `alembic check` (models and migrations agree) and downgrades to
  base. Columns match `models.AIGuardTrip` (String(64) PK, timestamptz NOT NULL, String(80) NOT NULL). `db-grants.sql`
  default privileges cover the new table for the app role.
- Mutation testing (scratch copy, `tests/test_ai.py -k "trip or explicit_price"`). 9 of 10 mutants were killed:
  | Mutant | Result |
  |---|---|
  | trip never recorded | killed (2 fail) |
  | `ensure_ai_enabled` skips the persisted check | killed (2) |
  | fingerprint without endpoint | killed (1) |
  | fingerprint without checked price | killed (1) |
  | read error fails open | killed (1) |
  | read error latches `disabled` | killed (1) |
  | DB trip not latched in memory | killed (1) |
  | L1 reverted (`price_explicit` unscoped) | killed (2) |
  | exception text logged on read error | killed (1) |
  | **fingerprint without deployment** | **survived** (see N1) |
- Secrets and privacy: the fingerprint is SHA-256 of normalised URL (endpoint + API path), lower-case deployment and
  `repr(checked_price)`. It contains no key, token or client id. The row holds only the `_clean_model` name, which is
  printable and at most 80 characters. Log lines carry only the exception type and the model name, with no prompt or
  answer text. Tests assert this.
- Fresh process with the same DB: `test_trip_survives_a_restart_and_a_second_replica` shows the second app makes zero
  Azure calls, returns 503 and then latches. A config change clears the trip (endpoint and price are each proven by a
  mutant; deployment is not isolated, see N1).
- Fail-open and fail-closed choices: closing on a read error and staying open per process on a write error are
  reasonable, and the docs explain both. However, the stated reason ("`reserve()` needs the same DB anyway") does not hold
  when the read fails because the pool is exhausted rather than because the DB is down. Blocking item 1 covers this.
- README and ADR 0002 text match the code (fingerprint inputs, how to clear, fail-closed behaviour, L1 scoping).

## Blocking

1. **Nested pool checkout in the summarise route can starve the pool. Every AI call then fails closed after 10 s.**
   - Where: `backend/app/routes/notes.py:113` calls `ensure_ai_enabled(...)`, which reaches `AzureOpenAI.check_persisted_trip`
     (`backend/app/ai.py:347-363`) and then `TripStore.tripped` (`ai.py:105-107`). That opens a **new** session from
     `app.state.db.sessions`. At that point the request's own session `db` already holds a pooled connection with an
     open transaction (from `_get` and `subscription_of`), so each request needs two connections at once.
   - Why it matters: the pool is `db_pool_size` 5 + `db_max_overflow` 5 = 10, with `pool_timeout=10`. FastAPI runs sync
     endpoints on a 40-thread pool. With 10 or more summarise requests in flight, each holds one connection and waits for
     a second, and none can be served. After 10 s each gets `TimeoutError`. `check_persisted_trip` treats that as an
     unreadable guard and returns 503 `ai_budget_reached`, "switched off until the team fixes its configuration". The
     database is healthy and nothing has tripped. This is a self-inflicted outage under ordinary load, and it breaks the
     rule at the top of `app/db.py` about not holding connections across extra work.
   - Reproduced: settings `db_pool_size=1, db_max_overflow=0` and a single summarise with a healthy model (`gpt-5-mini`).
     The result was **503 after 10.2 s**, with the log line `AI refused: the guard-trip record could not be read (TimeoutError)`.
     Before T-163 the same request needs one connection and succeeds.
   - Fix (either is fine):
     - (a) Let `ensure_ai_enabled(provider, db=None)` and `check_persisted_trip(db=None)` run the PK read on the
       caller's session when one is given (`db.get(AIGuardTrip, fp)`, with no extra commit), and pass `db` from the route.
     - (b) Drop the route-level persisted check and rely on the one inside `complete()`. That runs after `reserve()`
       committed and released the connection; its `AppError` is settled as `note_summary:failed` with 0 tokens.

     Either way, add a regression test with `db_pool_size=1, db_max_overflow=0` that expects 200 for a healthy model and
     503 for a tripped one.

## Non-blocking

- N1. `test_changing_the_ai_config_clears_the_trip` does not isolate the deployment dimension. In `_store_app` the
  deployment `gpt-5-nano` is not in the helper's price map, so `checked_price` becomes `None`. The guard is then off
  entirely and the fingerprint changes through the price alone. Removing the deployment from the fingerprint survives
  every test. Use an unknown deployment name with the same explicit price (for example `chat` at 2.0 against `chat2` at
  2.0) so only the deployment changes. Also assert `checked_price is not None` in that loop.
- N2. A read failure returns the "switched off until the team fixes its configuration" message, which sends operators
  to the wrong place on a database blip. Keep the code `ai_budget_reached` but use a neutral message ("The AI is
  unavailable right now. Everything else still works.").
- N3. Each request does two PK reads until the process latches: one at the route and one in `complete()`. That is
  cheap. If fix 1(b) is chosen it drops to one.
- N4. `BRIEF.md:165` still says "0001 to 0007 today". Update it to 0008.
- N5. The migration's `tripped_at` has `server_default now()`, while the model has a Python `default=utcnow` and no
  server default. This is harmless (`alembic check` does not compare server defaults, and inserts set it), but it
  differs from the other tables. Either drop the server default or add `server_default=func.now()` to the model.
- N6. Once a replica has latched, it stays off after the row is deleted until it restarts. This is documented in the
  README and accepted (decision 4).
