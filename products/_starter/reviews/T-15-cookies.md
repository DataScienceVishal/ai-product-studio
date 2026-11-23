# Review: T-15 cookie slice (session cookie clears, selling-lock lists, route sync test, normalise)

- Branch `p/_starter/T-15-cookies`, commits b25db59, 3e6887b, 00dd997. Diff: `git diff origin/main...origin/p/_starter/T-15-cookies`.
- Reviewed in a separate worktree (`/home/user/wt-rev15`), own venv, own database `starter_test_rev15`.
- Reviewer: reviewer agent, 2026-11-23.

## Verdict: PASS

The change is tests plus one product line (`normalise` in `frontend/src/ui.tsx`) and docs. Every claimed
guard fails when the code it protects regresses (mutation table below). No security, tenancy or performance
impact. The suggestions are not blocking.

## Evidence

| Check | Result |
|---|---|
| Backend suite (`pytest`, own DB) | **204 passed, 1 skipped** (205 collected). The skip is `test_spa.py:104`, "frontend not built", as before |
| Frontend `vitest run` | **111 passed** in 5 files |
| Frontend `tsc --noEmit` | clean |

### Mutation checks (each applied alone, then reverted)

| Mutation | Result |
|---|---|
| `auth.py:176` logout clear `secure=False` | FAIL `test_logout_clear...[secure]` |
| `auth.py:176` logout clears hard-coded `"session"` | FAIL `test_logout_clear...[secure]` |
| `account.py:71` owner delete clear `secure=False` | FAIL `test_account_deletion_clear...[secure]` |
| `account.py:103` member leave `path="/api"` | FAIL `test_member_leaving_clear...` |
| `account.py:104` member leave `httponly=False` | FAIL `test_member_leaving_clear...` |
| `account.py:103` member leave `secure=True` always | FAIL `...[plain-http-dev]` |
| `notes.py:27` `LIMITED_PROVIDERS = {"mock"}` | FAIL `test_every_provider_that_refuses_live_keys...` |
| `billing.py:188` Stripe accepts live keys | FAIL same test |
| App.tsx new route with `'...'` or `` `...` `` quotes | FAIL `test_client_routes_match_the_frontend_router` |
| App.tsx `path.startsWith("/reports")` / `/re/.test(path)` | FAIL same test (the new "other comparison" assertion) |
| App.tsx removes a route | FAIL same test |
| `normalise` reverted to the main version | 3 FAIL (`"//"`, `"///"`, `""`) in `routing.test.tsx` |

## Critical issues

None.

## Suggestions (not blocking)

1. **The route scanner still misses some comparison shapes.** `backend/tests/test_spa.py:189-191`. Verified
   that these App.tsx additions pass the sync test silently: `"/new-page" === path` (reversed operands),
   `path === ROUTES.reports` (constant, not a literal) and `PAGES[path]` (lookup table). A refresh on such a page
   would 404 in production. Cheap fix: also flag `===\s*path\b`, and flag `path\s*===\s*(?!["'`])` (a non-literal
   right side), and `\[\s*path\s*\]`. The NEXT.md wording "fails on other path comparisons" overstates it until then.
2. **Count wording.** NEXT.md says "205 backend ... tests pass"; the run is 204 passed, 1 skipped (README's
   "(205)" as a collected count is fine).
3. **Small test tidy-ups** in `backend/tests/test_cookies_and_limits.py`: `outbox` is unpacked and unused in
   `test_account_deletion_clear...` (line 75); `secure` is unpacked and unused in `test_member_leaving_clear...`
   (line 85), which also lacks the `("secure" in clear) is secure` check the other two have (still covered
   indirectly through set/clear equality, but the absolute check guards a set-side regression too).
4. `_assert_clear_matches_set` only compares `samesite=lax`. If both set and clear moved to `strict`, the
   equality loop would not notice a mismatch on SameSite value. Comparing the `samesite=` attribute by prefix
   would make it value-agnostic.
5. The `normalise` change alters runtime routing for `//` (now `/`). It is covered by vitest; the e2e was not
   re-run, which is acceptable for this size of change, but run it on the merge to main as CI already does.
