# T-93 review: `p/_starter/T-93-docs` (f16a85a)

Reviewer: reviewer. Date: 2026-11-25. Diff: `git diff $(git merge-base f16a85a origin/main) f16a85a`
(merge base `ba66373`; no `products/_starter` changes on main since, so the code under the docs is main's code).
Scope: docs only (README.md, ADR/0001, NEXT.md). Every factual claim checked against the code and re-run test counts.

## Verdict: PASS

The diff is accurate. Every number in the new tests table matches a fresh run, and every ADR 0001 update matches the
code. Nothing blocks the merge. There are four suggestions below. S1 is a one-line fix to BRIEF.md that I recommend
making before the merge, because this change turns one BRIEF sentence false.

## Test counts (re-run on this tree, local Postgres 16)

| Row | README says | Measured | Evidence |
|---|---|---|---|
| Backend pytest | 647 passed, 1 skipped | **647 passed, 1 skipped** (648 collected) | `pytest -q`: "647 passed, 1 skipped, 1 warning in 73.46s"; `--collect-only` per-file counts sum to 648 |
| Frontend vitest | 203 passed in 7 files | **203 passed, 7 files** | `npx vitest run`: "Test Files 7 passed (7) / Tests 203 passed (203)" |
| Deploy workflow checks | 102 passed | **102 / 0** | `bash infra/test-deploy-workflow.sh` (actionlint not installed, skipped by the script) |
| Deploy role checks | 67 passed | **67 / 0** | `bash infra/test-deploy-role.sh` |
| DB setup checks | 33 passed | **33 / 0** | `bash infra/test-db-setup.sh` |
| Bicep identity check | CI, needs `az bicep` | not run (no `az`) | wired in `_starter-ci.yml:185` after `az bicep build` |

"Where it runs" is right for every row. CI triggers on every push that touches the starter (`_starter-ci.yml:7-9`).
vitest runs in the `frontend` job (`npm test` = `vitest run`, `_starter-ci.yml:97-99`). The three infra scripts run on
every push (`:58`, `:193`, `:195`). The Bicep check needs the compile step (`:185`).

### 647 vs 648: same result, counted differently. No test was lost.

- T-95's board note says "backend 648 (0 fail, 1 skip)". That is the **collected** total, 647 passed + 1 skipped. The
  builder's "647 passed, 1 skipped" is the same run counted the pytest way. No backend code changed between T-95's merge
  and this branch, and the collected count is 648 on both.
- The skip is environment-dependent: `tests/test_spa.py:98-103` `test_the_real_vite_build_has_no_inline_script` skips
  when `frontend/dist/index.html` doesn't exist ("frontend not built"). With a built frontend it would be 648 passed.
- The README figure is honest: it says what pytest prints in a fresh checkout and in CI.

## Claims checked

**README "Not done yet" (README.md:148-154)**
- Frontend unit tests exist: 7 `*.test.ts(x)` files under `frontend/src` and `pages/`, run in CI. Correct.
- "Redis code is built and tested": `app/ratelimit.py` (Redis sliding window, fail-safe fallback). There are 35 tests in
  `tests/test_ratelimit_redis.py`. They run against `fakeredis` (`:12`), not a real Redis server. Acceptable.
- A real email adapter is still open, and the Azure deploy still waits for Q-5. Correct.

**ADR 0001 decision 6 update**
- Responses API at `/openai/v1/responses`: `ai.py:9-12,272`. `AZURE_OPENAI_API` is `auto|chat|responses` with
  default `auto`: `config.py:72`, `ai.py:262-265`. Correct.
- Layered caps. Monthly per plan: `ai.py:504`. Daily for limited tenants: `ai.py:506`, `notes.py:118`. Trial pool
  (`ai_global_daily_tokens x ai_trial_share`): `ai.py:508`, `notes.py:120`. Studio-wide daily cap on all tenants:
  `ai.py:510`, `notes.py:117`. Correct.
- In-flight limit: `ai_calls_per_tenant_at_once` = 2 (`config.py:102`), enforced at `ai.py:498-502`. Correct.
- `LIMITED_PROVIDERS = {"mock", "stripe"}` in `routes/notes.py:28`. Trials and those providers are both treated as
  limited (`:110`). Correct.

**ADR 0001 decision 8 update and Consequences**
- `RATE_LIMIT_REDIS_URL` empty means in-memory (`config.py:58-60`). If Redis errors or times out, the call is
  answered in memory and Redis is skipped for 5 s, so there is no 500 (`ratelimit.py:9-12,38,207`). Correct.
- Azure Cache for Redis is not provisioned, and it costs money (BUDGET.md). Correct.

**NEXT.md line 18**
- The "Choose" buttons have `disabled={!isOwner || blocked}` (`frontend/src/pages/app.tsx:280`). `blocked` is
  `email_verification_required && !email_verified` (`:232`). The server still returns 403. Correct.

## Critical issues

None.

## Suggestions

- **S1 (recommended before merge, low).** `BRIEF.md:59` still says "the README's tests table says 561 backend
  tests passed (stale: ... T-86 ... 566 backend and 182 frontend vitest)". After this change the README says 647/1
  and 203. Change the sentence to "the README's tests table records 647 backend (1 skipped without a frontend
  build) and 203 vitest tests passing (2026-11-25)".
- **S2 (follow-up task, low but real).** The one skipped test always skips in CI. The `backend` job never builds the
  frontend (`_starter-ci.yml:27-42`), and the Docker build that does build it doesn't run pytest. So the
  "no inline script, which the CSP would block" guard on the real Vite build has never run in CI. Fix it in one of
  two ways: add a step after `npm run build` in the `frontend` job that greps `dist/index.html` the same way, or build
  the frontend in the backend job. Suggested board task: *"_starter CI: test_spa.py:98 inline-script check always
  skips in CI (no frontend/dist in backend job); run it after npm run build."*
- **S3 (nit).** README "Not done yet" now says the same thing twice: "the code is built and tested, see
  `RATE_LIMIT_REDIS_URL`" and then "Rate limiting in Redis is built; only the Azure resource is missing." Drop the
  last sentence.
- **S4 (nit).** The ADR 0001 decision 6 update leaves out the startup cost guard from T-91/T-95, a newer cost-control
  layer that sits next to the caps. `app/aicost.py`: the app refuses to start when `AI_GLOBAL_DAILY_TOKENS x 31 x price`
  is above `AI_MONTHLY_BUDGET_USD` (6.10), with a price table per deployment (`config.py:92-99,143`). One more clause
  would make the "caps are layered" list complete.
