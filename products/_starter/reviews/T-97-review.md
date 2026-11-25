# Review: p/_starter/T-97 (commit 273d4f0)

Reviewer run, 2026-11-25. Diff: `git diff main...p/_starter/T-97` (6 files, +102/-10).

## Summary

The CSP check on the built `index.html` used to skip in every CI run because the backend job never builds the
frontend. This branch moves the check into a stdlib script, `scripts/check_built_html.py`, runs it in the
frontend job straight after `npm run build`, unit-tests its rules in the backend suite on synthetic HTML, and
makes `REQUIRE_FRONTEND_BUILD=1` turn the local skip into a failure. It also makes three doc fixes (README,
ADR 0001, FAQ). The change does what T-96/T-97 ask for.

## Evidence (re-run by reviewer)

- Backend: `REQUIRE_FRONTEND_BUILD=1 pytest`: **659 passed**, 0 skipped, 0 failed (Postgres localhost).
- With `frontend/dist` moved away: `REQUIRE_FRONTEND_BUILD=1` gives FAILED (as intended); without it, SKIPPED with
  the new reason.
- Frontend: `vitest run`: **203 passed** (7 files).
- `cd frontend && python3 ../scripts/check_built_html.py dist/index.html` gives `ok`, rc=0, on the real Vite build
  (module script with `src`, stylesheet `<link>`, no inline code).
- CI path: the frontend job's `defaults.run.working-directory` is `products/_starter/frontend`, so
  `../scripts/check_built_html.py` and `dist/index.html` resolve correctly. The `on.push.paths` filter
  `products/_starter/**` covers the new script. ubuntu-latest ships `python3`, and the script needs no packages
  (it runs on local 3.11, with `from __future__ import annotations` for the `list[str]` hints).
- `app/spa.py:29` `HTML_CSP` = `script-src 'self'; style-src 'self'` with no `'unsafe-inline'`, so flagging
  `<style>` blocks, `style=` attributes and `on*=` handlers is correct.
- ADR claim: `app/config.py:142` calls `aicost.check_ai_budget(deployment, price, ai_global_daily_tokens,
  ai_monthly_budget_usd)` and re-raises as a `ValueError` when the settings load. The ADR wording ("refuses to
  start if the studio-wide daily cap, priced at the configured deployment's rate, would exceed the monthly AI
  budget") matches the code. Small caveat: config.py says the check runs only with `AI_PROVIDER=azure`, and the
  ADR doesn't say so. That is acceptable.
- README: the duplicate Redis sentence is gone and the remaining sentence still says the same thing. The FAQ now
  says "UK and EU".

## Regex behaviour (probed by hand)

| Input | Result | Correct? |
|---|---|---|
| `<script\nsrc="/a.js">`, `<script\tsrc=/a.js>`, uppercase `SCRIPT SRC` | clean | yes |
| `<script data-src=...>x()</script>` | flagged | yes (`\ssrc` needs whitespace) |
| `<script >x</script >`, `<img\nonerror="x">`, `<DIV STYLE='x'>` | flagged | yes |
| `<meta content="Write notes once = fast">` | flagged (false positive) | fails closed, see S1 |
| `<script type="x" title=" src=">x()</script>` | clean (false negative) | contrived; Vite never emits it |
| `<a href="javascript:alert(1)">` | clean (false negative) | CSP blocks it too; not checked, see S2 |

## Critical issues

None.

## Suggestions (non-blocking)

- **S1** `scripts/check_built_html.py:19-20`: `_STYLE_ATTR` and `_EVENT_ATTR` match `\sstyle=` / `\son[a-z]+=`
  anywhere inside a tag, including inside quoted attribute values. A future `<meta name="description" content="...
  once = ...">` would fail CI. This fails closed and is unlikely in a Vite shell, but stdlib
  `html.parser.HTMLParser` would give exact attribute names with less code and no false positives or negatives.
  Worth doing if a product ever adds richer `<head>` metadata.
- **S2** Consider also flagging `javascript:` URLs in `href`/`src`, which the CSP blocks as well. They are rare in a
  built shell.
- **S3** Data-only scripts (`<script type="application/ld+json">`, `importmap`) would be flagged. That is fine
  today, but say so in the docstring so a product adding structured data knows why CI fails.
- **S4** `_built_html_checker()` re-executes the module for every parametrised case. Cache it with a module-level
  fixture or `functools.cache`. This is cosmetic.

## Verdict

**PASS**
