# Review: p/_starter/T-18-app (fb5daf7)

Reviewer: reviewer agent, 2026-11-24. Diff: `git diff origin/main...fb5daf7 -- products/_starter` (11 files, +322/-6).
Scope: board T-18, app side. Passwordless Postgres sign-in with Entra ID (`DB_AUTH=entra`), ADR 0002 decisions 5 and 6.

## Verdict: CHANGES

Two small blocking items: B1, a validator bypass that also leaks, and B2, a readiness probe that returns the wrong
status. Each is a few lines. Everything else is sound and can merge once B1 and B2 are fixed and tested.

## Summary

The design is right. A `do_connect` listener sets `cparams["password"]` from a `ManagedIdentityToken` with its own
audience and cache. Unsafe URLs are refused twice, in the `Settings` validator and in `Database`, and the error
messages never echo the URL. The same hook is used by `migrations/env.py` and by `maintenance purge`, which goes
through `Database`. Password mode really is unchanged: the default `db_auth="password"` adds no listener and no
`pool_recycle`, and a test asserts `_recycle == -1` and that the URL password reaches psycopg. A failed token
fetch is re-raised as `DbTokenError ... from None`, and only the exception class is logged. The tests use fakes
and check behaviour (parameters at the psycopg boundary, fetch counts, log text) rather than implementation.

### Evidence

- Full backend suite on this tree, private DB `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_t18r`:
  **388 passed, 1 skipped** (`tests/test_spa.py:103` frontend not built), exit 0, 53.7 s.
  `tests/test_db_entra.py` on its own: 16 passed.
- Probe of `validate_entra_url` (scratch script, psycopg 3.3.9, libpq 18.0, SQLAlchemy 2.1.9):

  | URL variant | Result |
  |---|---|
  | `id:%68unter2@h` (URL-encoded password) | refused (correct) |
  | `?sslmode=verify-full&sslmode=disable` | refused (the tuple is not `"verify-full"`, correct) |
  | `@h/app?user=id&...` (user only in the query) | refused (correct) |
  | `?SSLMODE=disable&sslmode=verify-full` | accepted. libpq rejects the unknown upper-case keyword, so this fails closed and does not downgrade. OK |
  | `id:@h` (empty password) | accepted. The token replaces it. Harmless |
  | **`?sslmode=verify-full&password=hunter2`** | **accepted** (see B1) |

- `/healthz` with a provider that fails (scratch script through `create_app` + `TestClient`): **HTTP 500
  `internal_error`**, logged as `app.http "unhandled error"` with a full traceback. Expected: 503 with `"db":"down"` (see B2).
- Audience: `https://ossrdbms-aad.database.windows.net` is the documented resource for Azure Database for
  PostgreSQL Entra tokens (scope `.../.default`, `az account get-access-token --resource-type oss-rdbms`). Correct.
  The Container Apps identity endpoint takes it as `resource=` with api-version 2019-08-01, which is the contract
  `ManagedIdentityToken` already follows.

## Critical issues (blocking)

**B1. A password in the query string gets past the validator and shows in `repr(engine)`.** `backend/app/dbauth.py:45`
checks only `parsed.password`. SQLAlchemy keeps `?password=hunter2` in `url.query`. The token still overwrites it
in `cparams`, so the database never receives it (verified: the cparams passed to psycopg contain `password: TOKEN`).
But the URL holds a credential that the "no password anywhere" mode promises is absent. SQLAlchemy masks only
`url.password`, so `repr(engine)` prints
`Engine(postgresql+psycopg://id@h/app?password=hunter2&sslmode=verify-full)`, and so does anything that logs the
engine or URL (SQLAlchemy `echo`/INFO logging, Alembic, error reports).
Fix: refuse `password` in the query as well, and preferably `passfile` too, with the same message. Add the case to
the parametrised `test_unsafe_urls_refused_without_leaking`, together with an assertion that `hunter2` is not in
the error.

**B2. A token failure skips `/healthz`'s database-down path.** `DbTokenError` subclasses `RuntimeError`
(`dbauth.py:33`). `backend/app/routes/health.py:29` catches only `SQLAlchemyError`, and that is the only code in
the app that classifies database failures. Because SQLAlchemy does not wrap non-DBAPI exceptions raised in
`do_connect`, the probe returns 500 `internal_error` instead of 503 `{"db":"down"}`. On-call then sees an
"unhandled error" traceback rather than the health-check message, and smoke.sh's `"db":"down"` diagnosis no longer
matches. This is exactly the failure mode the feature adds. Wrapping the AI exception, not letting `AIUnavailable`
through, is still correct: otherwise users would get an "AI service" 503 for a database problem.
Fix: either make `DbTokenError` subclass `sqlalchemy.exc.SQLAlchemyError` (it keeps the safe message and
`from None`), or catch `(SQLAlchemyError, DbTokenError)` in `healthz`. Add a test: an entra app with a failing
provider makes `/healthz` return 503 with `db: down`, and neither the token nor the header appears in the logs.

## Suggestions (non-blocking)

1. **README example URL** (`README.md`, "Entra ID database sign-in"): add `&sslrootcert=...`. libpq's
   `verify-full` with no root file looks for `~/.postgresql/root.crt`, which the image doesn't have, so the URL as
   documented would fail to connect. The deploy workflow already appends
   `sslrootcert=/etc/ssl/certs/ca-certificates.crt` (`.github/workflows/_starter-deploy.yml:333`). Copy that
   (or use `sslrootcert=system`, libpq 16+) so the README matches. This is not a security hole, because libpq fails closed.
2. **Concurrency test.** The token cache is thread-safe: `ManagedIdentityToken.get` holds one lock across the
   check and the fetch, and the listener is stateless. But no test here fires concurrent pool connects. Add a
   test with N threads and `pool_size=N`, a slow `MockTransport`, and an assertion of exactly one fetch.
3. **Failure caching affects the database now.** One failed fetch from the identity endpoint is cached for
   `FAILURE_TTL` (10 s), and the lock wait times out after 5 s. Both are acceptable, but for this feature they mean
   "every new DB connection fails for up to 10 s after one identity blip". Note it in the `dbauth.py` docstring
   or README. Existing pooled connections are not affected.
4. **Margin and recycle.** These are fine. The token is checked only at connect time, and a connect token always
   has at least 120 s of life left against a 5 s connect timeout. `pool_recycle=45 min` isn't needed for
   correctness, but it bounds connection age and it is harmless. Optional: say in the comment at `dbauth.py:26`
   that recycle is hygiene, not a token requirement. The module docstring already says so.
5. **Log wording.** Errors from the token path are logged by `app.ai` with AI wording ("managed identity endpoint
   is not available"), then by `app.dbauth`. If `resource` is added to the log `extra` in `_fetch` (it isn't
   secret), on-call can tell the audiences apart.
6. `migrations/env.py:29,35` constructs `Settings()` up to twice. Construct it once and reuse it.
7. Server-side rejection (for example, the role was never created) doesn't invalidate the cached token. That's
   fine, because a new token wouldn't help. A short comment would stop someone "fixing" it later.

## Security checklist

- Token, identity header or URL in logs or errors: none found. The listener logs the class only, and the cause is
  suppressed. The `_fetch` paths log the class or status only. psycopg auth errors name the user, not the password.
  The pool's `Error on connect()` debug log carries only the safe `DbTokenError` text (covered by the caplog
  tests at DEBUG). `repr(Settings)` and `repr(engine)` carry no secret, except in the B1 case.
- Password mode: unchanged (tests plus the code path).
- Validator bypass: B1 (query `password=`). `sslmode` cannot be overridden from `connect_args`, because
  `Database` doesn't set it and the URL wins over `PGSSLMODE`. Duplicate or upper-case `sslmode` fails closed.
- Thread safety: OK (see suggestion 2).
- `AIUnavailable` vs `DbTokenError`: the wrapping is correct, the classification isn't (B2).
- Audience: correct.
