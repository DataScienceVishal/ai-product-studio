# Review: p/_starter/T-15-async-login (a7a41dd = 245cd62 merged with main)

Reviewer: reviewer agent, 2026-11-24. Diff: `git diff main...HEAD -- products/_starter` (8 files, +191/-18).
Scope: board T-15, the "login bursts claim a hash slot before taking a worker thread" item.

## Verdict: CHANGES

## Summary

The mechanism is sound. `security.hash_capacity` is an async yield dependency. It takes an
`anyio.CapacityLimiter(HASH_SLOTS)` slot on the event loop, gives up after `HASH_WAIT_SECONDS` with the existing
503 `busy` and `Retry-After: 5`, and releases the slot in `finally`. All six routes that hash or verify use it:
signup, login, reset-confirm, invitations/accept, `DELETE /api/account` and `DELETE /api/account/me`. A test
inspects the route sources and stops a new hashing route from skipping it. Removing the acquire makes both burst
tests fail (mutation checked).

One design problem blocks the merge. The slot is taken **before every cheap gate**: the per-IP and per-email
rate limits, the session check on the account deletes, and the weak-password check. Requests that will never
hash now queue for one of the 2 slots. So the rate limiter no longer protects the hash queue, and anyone without
credentials can fill the queue. A second problem: the suite cannot see a slot leak, which is the failure that
matters most for this code.

### Evidence

- Backend, this exact tree, against a private DB (`TEST_DATABASE_URL=.../starter_test_t15rev`, because another
  agent was using `starter_test` at the same time): **308 tests: 307 passed, 1 skipped** (`test_spa.py:104`
  frontend not built), 0 failed, rc 0. On main, 304 tests are collected.
- Frontend `npx vitest run`: **5 files, 111 tests passed**.
- Mutation A (scratch copy): `hash_capacity` reduced to a bare `yield`. Both burst tests **fail**
  (`/healthz took 1.38s during the burst`).
- Mutation B (scratch copy): the `try/finally: limiter.release()` removed, so every slot leaks. The **full suite
  still passes (0 failures)**. See C2.
- Probe (scratch, not committed): `SlowHasher` at 0.2 s. It sends 6000 `DELETE /api/account` with **no
  cookie**, then 4 real logins.

  | tree | real logins | junk results |
  |---|---|---|
  | main | 4 x 401 (correct result), 4.5 s | 6000 x 401 |
  | branch | **2 x 503**, 2 x 401, 3.4 s | **3488 x 503**, rest 401 |

  On the branch, unauthenticated requests that never reach argon2 hold hash slots, and real users get turned away.

## Critical issues (must fix)

**C1. The hash slot is taken before rate limits and auth, so cheap rejects fill the 2-slot queue.**
- Where: `app/routes/auth.py:114,149,222`, `app/routes/team.py:120`, `app/routes/account.py:48,88`. The rate
  limits run inside the endpoint (`auth.py:117-118,152,224`, `team.py:122`, `account.py:52,91`), and
  `current`/`owner` run after `hash_capacity`. The test enforces this order:
  `tests/test_async_hash_capacity.py:118` (`calls.index(security.hash_capacity) == 0`).
- Why it matters: before this change, one IP sending a flood got fast 429s that never touched the hash
  semaphore. Rate-limited requests are now serialised behind 2 slots, and each one holds its slot while it gets a
  DB connection on a thread. `DELETE /api/account` with no cookie at all, and with no rate limit before auth,
  takes a slot too. A single client can make real sign-ins return 503 (probe above). The slot is also held for
  the whole request, including the DB writes and `send_verification` after the hash. That lowers throughput
  compared with main, where `_Slot` wrapped only the argon2 call.
- Fix: run the cheap gates before taking capacity. For example:
  (a) An async dependency `auth_limits` that does the `client_ip` and email rate-limit checks. `RateLimiter.hit`
  is in-memory with a short lock, so it is safe on the loop. Login can take `data: SignIn` in the dependency,
  because FastAPI parses the body once. List it before `hash_capacity`.
  (b) On the account deletes, take capacity after `current`/`owner`. `current` commits, so its pooled connection
  is back in the pool by then. A small `owner_then_hash_capacity` dependency, or `Depends(hash_capacity)` as a
  parameter after `me`, would do it.
  (c) Rewrite the ordering test as "after the rate-limit/auth gate, before the endpoint body".
  (d) Add a regression test: a flood of over-limit logins from one IP, or unauthenticated deletes, must not turn
  a concurrent real login into a 503.
  When Redis-backed limits land later in T-15, the check becomes I/O and has to be async anyway, so this shape
  fits.

**C2. No test catches a leaked slot.**
- Where: `tests/test_async_hash_capacity.py:67-79` and the suite as a whole. Each `TestClient` request runs on a
  fresh event loop, and `_limiter()` is per loop (`app/security.py:46-54`). A leaked slot is thrown away with
  its loop. Inside the burst test, a leak still gives "some 401, some 503", so it passes.
- Why it matters: in production there is one loop per worker. A release that is missing, or skipped on one path
  (error raised in the endpoint, 422 validation, 429, client disconnect), would lock **every** sign-in on that
  replica after 2 requests, permanently. Mutation B shows the suite stays green.
- Fix: in the burst tests, after `gather`, assert `security._limiter().borrowed_tokens == 0` on the same loop.
  Then, on that same loop, send one request each that ends in 401 (wrong password), 422 (weak password at
  signup), 429 (over-limit) and 503 (timeout), and assert `borrowed_tokens == 0` after each one. Optionally,
  cancel a waiting request (task.cancel during the wait) and assert the waiter queue is empty.

## Checked and fine

- Release on every path: `acquire` is inside `move_on_after`. anyio releases a token that was granted at the
  same moment as a cancel, so a timeout leaks nothing, and `cancelled_caught` maps only the deadline to 503. A
  client-disconnect `CancelledError` while waiting propagates without a token being held. After acquire, there is
  no await before `try`, and `finally` releases on success, `AppError` and cancellation. No double release.
  Acquire and release run in the same task (the full ASGI stack under httpx shows no borrower `RuntimeError`).
- Fairness: anyio's `CapacityLimiter` wakes waiters in FIFO order.
- Exhausted capacity: 503 `busy` with `Retry-After: 5`, the same body and header as the thread backstop
  (`_busy()`, `security.py:38`). The test checks both.
- The thread `BoundedSemaphore` stays as a memory backstop. With one loop per process and equal slot counts, it
  never makes a request wait twice.
- Call sites: no `hash_password`/`verify_password` caller outside the six routes. `needs_rehash` runs only
  inside login, which is covered.

## Suggestions

- S1. `security.py:46`: the bare `"weakref.WeakKeyDictionary"` annotation could be
  `weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, anyio.CapacityLimiter]`. Also, `import asyncio` is out
  of alphabetical order with `hashlib`/`secrets`.
- S2. Once C1 is fixed, think about making the async admission limit a little larger than `HASH_SLOTS` (for
  example 2x). The thread semaphore stays the memory bound, and the non-hash work in each request (DB writes,
  session creation, email) would no longer cut login throughput.
- S3. The README test count (`README.md:36`, "209") and NEXT.md ("209 backend tests") are stale. The merged
  tree collects 308 (304 on main, which itself still says 205). Either drop the number or update it at merge
  time.
- S4. A hard-coded `asyncio.get_running_loop()` ties the limiter to asyncio. That is fine for uvicorn, but
  `anyio.lowlevel.current_token()` (or a per-app limiter created in lifespan on `app.state`) avoids both the
  backend assumption and the module-global weakref map.

## Re-review at b3de3e7: PASS

Reviewer: reviewer agent, 2026-11-24. Diff: `git diff f051b0b..b3de3e7` (7 files, +232/-41).

**C1 fixed.** `security.hash_capacity_after(gate)` makes the slot dependency depend on a per-route gate, so
FastAPI resolves the gate first. All six routes use it.
- Gates: `_signup_gate`, `_login_gate` and `_reset_gate` in `routes/auth.py`, `_accept_gate` in `routes/team.py`,
  and `_delete_account_gate`/`_delete_me_gate` in `routes/account.py`.
- The gates hold the rate limits, `current`/`owner`, the weak-password check and the confirmation check. The
  in-endpoint copies are gone, so nothing runs twice.
- On the account deletes, the endpoint depends on the same gate, and FastAPI's per-request dependency cache runs
  it once. Probe: 7 deletes with a wrong confirmation gave `422 x5, 429 x2`, so the 5/min limit is not
  double-counted.
- The route-ordering test now checks that the gate is the slot dependency's only sub-dependency.

**C2 fixed.** `tests/test_hash_capacity_slots.py` runs on one event loop. It asserts `borrowed_tokens == 0` after
the 201, 409, 422, 401, 503, 429 and 500 paths, and checks `tasks_waiting == 0` after a timeout.

### Evidence

- Backend, private DB `starter_test_t15rev2`: **311 tests: 310 passed, 1 skipped** (frontend not built), rc 0.
- Frontend `npx vitest run`: **5 files, 111 tests passed**.
- Mutation B (no `limiter.release()`): 2 tests fail (`test_every_exit_path_returns_its_slot_on_one_loop` and
  `test_a_flood_of_unauthenticated_deletes...`).
- Mutation C (slot taken without its gate): 3 tests fail (`exit_path`, `cheap_rejects`, `every_route...`).
- Original probe: cookieless `DELETE /api/account` flood, then 4 real logins with `SlowHasher` at 0.2 s.

  | flood size | junk results | real logins |
  |---|---|---|
  | 1500 | all 401, **0 x 503** | 4 x 401 in 1.4 s |
  | 6000 | all 401, **0 x 503** | 2 x 401, **2 x 503** in 4.2 s |

  For comparison, main at 6000 gave 4 x 401 in 4.5 s.

### Non-blocking note (N1)

The 6000 case is no longer junk taking slots. It is worker-thread saturation:
- The account-delete gates and `get_db` are sync, so each junk request still uses a worker thread, as on main.
- A real login that holds a slot then waits for a worker thread behind the flood. The time it waits counts
  against the next login's `HASH_WAIT_SECONDS`, so that login gets 503 with `Retry-After` instead of a slow 401.
- Any sync route degrades under a flood of that size, so this does not block.
- Options, if it matters later: an admission limit a little above `HASH_SLOTS` (suggestion S2 above), or async
  gates for the session lookup.

Earlier suggestions: S1 is done (the annotation and the import order). S3 still stands: README/NEXT give stale
test counts, and the tree now collects 311.
