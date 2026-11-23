# Review: T-16, the backend serves the built SPA (one image, one origin)

- Commits: ce9d57f (WIP) and e74e752 (final), verified with `git log`. Diff: `git diff 912c2fe e74e752 -- products/_starter .github`.
- Reviewed on a `git archive` export of e74e752 (not the shared tree), own database `starter_rev16`, ports 8700/4700.
- Reviewer: reviewer agent, 2026-11-23.

## Verdict: CHANGES

One blocker: the backend test suite is red, locally and in GitHub CI, because a test still opens the moved
`backend/Dockerfile`. The SPA serving itself is sound. Fix the test and this is a PASS with no further review
of the design needed; the suggestions below are not blocking.

## Summary

`app/spa.py` mounts `/assets` as `StaticFiles` with a one-year `immutable` Cache-Control, and puts an
`index.html` fallback in the 404 handler for GET and HEAD outside `/api` and `/assets`. The HTML gets `no-cache`
and the SECURITY.md I4 CSP. `RequestContext` now keeps a response's own `Cache-Control` and
`Content-Security-Policy` outside `/api`. A root multi-stage Dockerfile builds the frontend with Node and copies
only `dist/` into the Python image. A CI `image` job builds the image and smoke-tests it. The deploy workflow
now points at the root Dockerfile with `EXPECT_SPA=true`, which `infra/smoke.sh` step 5 uses. This meets ADR 0002
decision 2.

## Evidence

| Check | Result |
|---|---|
| Backend suite (export, own DB) | **1 failed, 176 passed, 1 skipped** (178). After a local `vite build`: 1 failed, 177 passed. The failure is `tests/test_hardening.py::test_the_image_does_not_let_uvicorn_trust_forwarded_headers`, `FileNotFoundError: 'Dockerfile'` |
| GitHub CI for e74e752 | `_starter-ci` **failure** on both runs: [45275277860](https://github.com/DataScienceVishal/ai-product-studio/actions/runs/45275277860) (push to `main`) and [45275281890](https://github.com/DataScienceVishal/ai-product-studio/actions/runs/45275281890) (branch). Jobs: infra success, **image success**, frontend success, **backend failure** at `python -m pytest -q`, e2e skipped |
| Docker image build and in-container smoke test | Docker isn't available locally. Verified only by the CI `image` job, which passed: build, `/livez`, CSP on `/verify-email`, `<div id="root">` on `/`, JSON 404 on `/api/nope` |
| `test_spa.py` with the real Vite build present | 31 passed, including `test_the_real_vite_build_has_no_inline_script` (skipped when there's no build) |
| Real build output | `dist/index.html` has only `<script type="module" crossorigin src>` and `<link rel="stylesheet" crossorigin>`. No inline script or style, no `.map` files, no `@font-face` or external `url()` in the CSS, no `eval` or `new Function` in the JS |
| `scripts/e2e.sh` (Vite preview, API-only) | `E2E PASS: core flow` |
| Core flow e2e on **one origin** (uvicorn with `FRONTEND_DIST`, no Vite), with a listener that fails the run on any CSP console violation | `E2E PASS: core flow`, no CSP violations. The CSP doesn't break the real app |
| Live probe, `ENV=prod COOKIE_SECURE=true`, real dist | see below |
| actionlint on both workflows | clean (rc 0) |

Live probe (prod settings, uvicorn on 8700):

- `/`, `/verify-email`, HEAD `/login`: 200 `text/html`, `cache-control: no-cache`, HTML CSP, HSTS, nosniff, `X-Frame-Options: DENY`, `x-robots-tag`.
- `/api/nope`, `/api/docs`, `/livez`, `/healthz`: JSON, `no-store`, `default-src 'none'` CSP. No `/api` or probe path ever returned HTML.
- `/assets/index-*.js`: `public, max-age=31536000, immutable`. `/assets/nope.js`: JSON 404, `no-store`.
- A symlink planted in `assets/` pointing at `/etc/passwd`, and a symlinked directory pointing at `/etc`: both 404 (StaticFiles defaults to `follow_symlink=False`). `/assets/%2e%2e/index.html`: 404. All ten traversal cases in the tests: no leak.
- POST `/livez`: 405 JSON. PUT `/verify-email`, OPTIONS `/login`: 404 (the fallback serves GET and HEAD only).

## Focus questions

- **Can a non-`/api` response drop or weaken security headers?** It can't drop any: `extra` re-adds every
  security header the response didn't keep, and only `cache-control` and `content-security-policy` can be kept
  (`main.py:137-140`). It can weaken those two, though. Any route outside `/api` that sets its own
  Cache-Control or CSP now wins over `no-store` and `default-src 'none'`. Today that's only the SPA fallback and
  `/assets`, which is intended. A future product route outside `/api` (a webhook, a share link) would inherit
  this silently. See S1.
- **Can an `/api` response keep a page CSP?** No. Under `/api`, `own` is empty, so every security header the
  response set is stripped and replaced. In non-prod, `API_CSP` isn't in `self.names`, so an `/api` route's own CSP
  would survive, but no `/api` route sets one. This guard isn't tested: mutation M7 survived (S2).
- **SPA fallback in the 404 handler:** right. Real routes with the wrong method still raise 405 before the
  404 handler. `_is_reserved` keeps `/api`, `/api/*`, `/assets` and `/assets/*` as JSON. `/livez` and `/healthz` are
  real routes, so they never reach the fallback. The fallback never opens a path taken from the request.
- **Immutable caching:** only on StaticFiles 200 and 304. A 404 from StaticFiles is raised as an exception, so it
  never gets the header (mutation M4 is equivalent). Vite puts only hashed files in `assets/`, and there's no
  `frontend/public/`, so nothing unhashed lands there.
- **Dockerfile:** `pip install --require-hashes`. Non-root `appuser` (uid 10001), and the app files stay
  root-owned and read-only to it. The Node stage and its devDependencies don't reach the runtime image; only
  `/build/dist` is copied. No source maps. Layer order is right: lockfiles, then install, then source.
  `.dockerignore` keeps out `node_modules`, `dist`, `.venv`, `.env*`, tests, reviews and infra. Neither base image
  is pinned by digest (S6).
- **CI image job:** the shell is correct and actionlint is clean. The default `bash -e` has no `pipefail`, but
  every pipe ends in `grep`, so `grep` decides the exit status. That is fine.

## Critical issues

### C1. The backend suite fails: a test reads the moved Dockerfile

- **Where:** `products/_starter/backend/tests/test_hardening.py:201`, `open("Dockerfile")`. The Dockerfile moved
  from `backend/` to `products/_starter/Dockerfile` in this change.
- **Why it matters:** the CI `backend` job is red on both runs, and this test guards the ingress-trust settings
  (`--no-proxy-headers`, `TRUST_PROXY_HEADERS=true`). The commit message says "178 backend tests ... pass
  locally", which isn't true at e74e752. Engineering rules: no merge without green tests.
- **Fix:** read the file by an absolute path, e.g.
  `(Path(__file__).resolve().parents[2] / "Dockerfile").read_text()`. Then re-run the suite and confirm CI is green.

### C2. Process: unreviewed product code is already on `main`, and `main` CI is red

- **Where:** `origin/main` contains ce9d57f (labelled "not reviewed yet") and e74e752. The CI run on `main`
  ([45275277860](https://github.com/DataScienceVishal/ai-product-studio/actions/runs/45275277860)) failed.
- **Why it matters:** CLAUDE.md section 9 says product code goes on `p/<slug>/<task-id>` and merges to `main` only
  after reviewer PASS and green tests.
- **Fix:** fix C1 forward on `main` (no force-push or history rewrite). Record the slip in `state/HURDLES.md`. Use a
  `p/_starter/T-xx` branch for the next starter change.

## Suggestions (not blocking)

- **S1. Narrow the header exemption.** It is based on the path (anything outside `/api`), not the response.
  Consider exempting only responses that the SPA code marks, e.g. HTML from `spa.fallback` and the `/assets`
  mount: check a scope flag set by `spa.py`, or `content-type: text/html` plus the `/assets` prefix. Then a future
  non-`/api` JSON route can't override `no-store` by accident.
- **S2. Test the `/api` side of the header rule.** Mutation M7 (`own = self.spa_own` for every path) survived. Add
  a test with a throwaway `/api/_probe` route that sets `Cache-Control: public` and a CSP, and assert that the
  response comes back with `no-store` and, in prod, `default-src 'none'`.
- **S3. Test symlinks.** Mutation M8 (`follow_symlink=True`) survived. Add a symlink inside `assets/` that points
  outside the folder (to `tmp_path/secret.txt`) and assert a 404.
- **S4. HEAD `Content-Length`.** HEAD gets `content-length: 0`, while GET has the real length. Return
  `Response(html)` for both methods and let the server drop the HEAD body. Mutation M3 is equivalent, because
  Starlette and uvicorn already drop it.
- **S5. Soft 404s.** `/robots.txt`, `/favicon.ico`, `/API/notes` and any unknown file get a 200 with the app's HTML.
  This is harmless, but a 404 for paths whose last segment has a file extension would make crawlers and monitoring
  less confusing.
- **S6. Pin the base images by digest.** Pin `node:22-slim` and `python:3.12-slim` by digest, as Trivy already is
  (the Python one was already unpinned before this change), and let Dependabot or a board task bump them.
- **S7. Show logs when the CI image job fails.** Add an `if: failure()` step with `docker logs starter-ci`, so a
  container that won't start is diagnosable.
- **S8. `/assets` redirect.** `/assets` answers 307 with an absolute `http://` Location (uvicorn runs with
  `--no-proxy-headers`). Behind the ingress this costs an extra http-to-https hop. It's a nit, but it could answer
  404 instead.

## Mutation check (full suite; baseline 1 failed because of C1)

| Mutation | Result |
|---|---|
| M1: drop the `/api` reservation in `_is_reserved` | caught (5 failed) |
| M2: fall back for every method | caught (2) |
| M3: send the body on HEAD | survived, equivalent (the server drops HEAD bodies) |
| M4: `immutable` on every status | survived, equivalent (StaticFiles raises its 404) |
| M5: strip every security header (the old behaviour) | caught (12) |
| M6: no de-duplication (`headers + self.headers`) | caught (12) |
| M7: keep own headers under `/api` too | **survived**: S2 |
| M8: `follow_symlink=True` | **survived**: S3 |
| M9: no CSP on the HTML | caught (2) |
| M10: `'unsafe-inline'` in `script-src` | caught (2) |
| M11: fallback on 405 as well | survived, equivalent today (no GET-less route outside `/api`) |

## Re-review (6935565, e135114): PASS

- Commits: 6935565 fixes C1 and e135114 has the follow-ups; both verified with `git log`. Diff:
  `git diff e74e752 e135114 -- products/_starter .github`. Reviewed on a `git archive` export of e135114, with
  database `starter_rev16` and ports 8700/4700.
- **C1 fixed.** `test_hardening.py:202` now reads `Path(__file__).resolve().parents[2] / "Dockerfile"`. A sanity
  mutation that points it at another file makes the test fail, so it really reads the root Dockerfile.
- **C2 closed.** The fix went forward on `main` with no force-push. The hurdle is logged as closed in
  `state/HURDLES.md` (2026-11-23T22:18:23Z), with the rule that the full suite must pass on the exact tree before
  any push to main.
- **S1 done, and the design is sound.** `RequestContext` keeps a response's own Cache-Control and CSP only when
  `scope["spa.own_headers"]` is set (`main.py:137`). Only `spa.fallback` and `ImmutableStatic` on a 200 or 304 set
  that flag. It is a server-side scope key, so a client can't set it with a header. It works because Starlette
  passes the same scope dict through the middleware, the Mount and `Request`, and the tests prove that end to end.
  Every other route, inside `/api` or not, now gets `no-store` and the API CSP back.
- **S2, S3 and S7 done.** `test_api_and_other_routes_cannot_keep_their_own_cache_or_csp` and
  `test_assets_do_not_follow_symlinks` are added, and the CI image job has an `if: failure()` docker logs step
  (`|| true`, so the step can't mask the real failure).
- **Still open, not blocking:** S4 (HEAD Content-Length 0), S5 (soft 404s), S6 (base images not digest-pinned)
  and S8 (`/assets` 307). Track them as a small starter task if wanted.

| Check | Result |
|---|---|
| Backend suite on the export (own DB) | 179 passed, 1 skipped (no frontend build). After `vite build`: **180 passed** |
| GitHub CI for e135114 | `_starter-ci` **success** on `main` ([45279346198](https://github.com/DataScienceVishal/ai-product-studio/actions/runs/45279346198): backend, image, frontend, infra and e2e all success) and on the branch ([45279352583](https://github.com/DataScienceVishal/ai-product-studio/actions/runs/45279352583): e2e skipped by design). 6935565 is also green on both |
| Docker image | built and smoke-tested by the CI `image` job, which passed. Not run locally (no Docker) |
| actionlint, both workflows | clean |
| `scripts/e2e.sh` (ports 8700/4700) | `E2E PASS: core flow` |
| Core flow on one origin (uvicorn with `FRONTEND_DIST`), with a listener that fails on CSP violations | `E2E PASS: core flow`, no violations |
| Prod-mode header probe | same as the first review. HTML: `no-cache` and the HTML CSP. `/api`, `/livez`, `/healthz`, asset 404s: `no-store` and `default-src 'none'`. Hashed assets: `immutable`. No `/api` or probe path returns HTML |

Mutations (full suite with the frontend built; baseline 180 passed):

| Mutation | Result |
|---|---|
| M7: honour own headers on every response | **caught** (1, the new test) |
| M7b: go back to the path-based rule from e74e752 | **caught** (1) |
| M8: `follow_symlink=True` | **caught** (1, the new test) |
| M12: the fallback doesn't set the marker | caught (11) |
| M13: assets don't set the marker | caught (2) |
| M14: set the marker on every StaticFiles status | survived, equivalent (StaticFiles raises its 404 instead of returning it) |
| M1: drop the `/api` reservation | caught (4) |
| M5: strip every security header | caught (12) |
| M10: `'unsafe-inline'` in `script-src` | caught (1) |
| M15: the hardening test reads the wrong file | caught (1) |

**Verdict: PASS.** T-16 meets ADR 0002 decision 2. The tests are green locally and in CI, and the key behaviour is
covered by tests that catch the mutations above.
