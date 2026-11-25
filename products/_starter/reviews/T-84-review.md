# Review: p/_starter/T-84 (commit 510774a)

Reviewer: reviewer agent, 2026-11-25. Diff: `git diff main...p/_starter/T-84`, which touches
`frontend/src/api.ts` (+2/-1) and `frontend/src/api.test.ts` (+40/-1).

## Verdict: CHANGES

The production change is correct: the catch block now resets `billingProvider` to `""`, so the flag fails closed. The
new tests catch a dropped assignment, a non-string fallback flipped to `"mock"`, and a dropped catch reset. They do
**not** catch the main mutation that T-83 S1 named and that T-84 exists to catch: flipping the module's initial value
`let billingProvider = ""` to `"mock"`. Every test in the file still passes with that mutation, and the test called
"is off before any config is loaded (fails closed)" is vacuous. The non-OK response path is also untested. Fixing
both takes about 10 lines.

## Evidence

- `npx vitest run` in `products/_starter/frontend`: **164 passed (164)**, 6 files. On main the count was 155.
- `npx tsc --noEmit -p .`: exit 0, no output.
- Mutations. Each one was applied to `src/api.ts`, `npx vitest run src/api.test.ts` was run (28 tests), and the file
  was restored afterwards. `git status` is clean apart from this review file.

| # | Mutation | Result |
|---|---|---|
| M1 | initial value `let billingProvider = "mock"` | **survives** (28/28 pass) |
| M2 | non-string fallback `: "mock"` | caught (6 fail) |
| M3 | delete the `billingProvider = typeof ...` assignment | caught (7 fail) |
| M4 | delete the new `billingProvider = ""` in the catch block | caught (1 fail) |
| M5 | catch sets `"mock"` | caught (1 fail) |
| M6 | `String(config.billing_provider)` (no type check) | caught (1 fail) |
| M7 | truthy check, `? "mock" : ""` | caught (5 fail) |
| M8 | `isMockBilling` becomes `!== ""` | caught (1 fail) |
| M9 | `isMockBilling` becomes `.toLowerCase().includes("mock")` | survives (minor) |
| M10 | non-OK response sets `"mock"` (`else` branch) | **survives** |
| M11 | `billingProvider = "mock"` before `if (response.ok)` | **survives** (only the non-OK path exposes it) |

## Critical issues

**C1: the initial-value mutation (fail open) is not caught, and the test meant to catch it is vacuous.**
`api.test.ts:162` sets the flag with `beforeEach(() => setBillingProviderForTest(""))`, and
`it("is off before any config is loaded (fails closed)")` at `:165-167` then asserts `false`. So that test only checks
the value the setter just wrote, never the module's own default. The rejected-fetch case can't cover this any more,
because the new catch reset overwrites the initial value. This matters for two reasons. The test name tells future
readers the default is guarded when it isn't. And with M1 applied, a non-OK `/api/config` (for example a 500 or 404)
leaves the flag at `"mock"`: the billing page would then show the mock checkout UI instead of the real path.
Fix: use a fresh module instance. I checked this probe in a scratch test file, since deleted: it passes on the
branch and fails under M1.
```ts
it("is off before any config is loaded (fails closed)", async () => {
  vi.resetModules();
  const fresh = await import("./api");
  expect(fresh.isMockBilling()).toBe(false);
});
```

**C2: the non-OK path is neither failed closed nor tested (M10 and M11 survive).** At `api.ts:37-41` the flag is
only written when `response.ok`. A 500 leaves whatever was there before. Today that is `""`, because
`loadClientConfig` runs once in `main.tsx`, but nothing pins this down. Fix: reset the flag at the top of
`loadClientConfig`, or in an `else` branch, so that every non-success path writes `""`, the same as the catch block.
Then add a case: `setBillingProviderForTest("mock")`, then `reply(500, {})`, then `isMockBilling() === false`.

## Suggestions (non-blocking)

- S1 (M9): nothing pins exact-match semantics. If someone "relaxes" `isMockBilling` to a case-insensitive or substring
  match, `"Mock"` or `"mockingbird"` would turn on mock billing. Add `"Mock"` to the `it.each` non-mock cases, or to
  the "real provider" test.
- S2: the "real provider or a missing field" test checks two scenarios in one `it`. Splitting it would make the
  failure messages clearer. This is cosmetic.
- Test isolation is fine. The new `describe` resets the flag in both `beforeEach` and `afterEach`. `fetchMock` is
  re-stubbed per test. `vitest.config.ts` has `restoreMocks` and `unstubGlobals`, and vitest isolates files by
  default, so the `billing.test.tsx` setter calls can't leak in. `mockResolvedValueOnce` and `mockRejectedValueOnce`
  are used correctly, and `loadClientConfig` clears its 5 s timer in `finally`. The one caution: if C1 is fixed with
  `vi.resetModules()`, use only the `fresh` import in that test. The statically imported `isMockBilling` points at the
  old module instance.
- The comment change at `api.ts:43` is fine. Security: no new endpoints or inputs, and the change narrows behaviour
  toward fail-closed.

---

## Re-review: commit d564316

### Verdict: PASS

C1 and C2 are fixed. The default test now imports a fresh copy of the module (`vi.resetModules()` then
`await import("./api")`), so it checks the real starting value. `loadClientConfig` now sets `billingProvider = ""`
before the fetch. That covers every non-success path: a non-OK answer, a thrown fetch, an abort, and an OK answer
whose body is not valid JSON (it ends up in the catch block with the flag already off). Removing the catch-block
reset is safe because of this upfront reset. New `it.each` cases for 500 and 404 send a `"mock"` body.

### Evidence

- `npx vitest run`: **166 passed (166)**, 6 files. `npx tsc --noEmit -p .`: exit 0.
- I re-ran the full mutation set against d564316, using `api.test.ts` (30 tests) and restoring the file after each
  mutation.

| # | Mutation | Result |
|---|---|---|
| M1 | starting value `"mock"` | caught (1 fail), previously survived |
| M2 | non-string fallback `"mock"` | caught (6) |
| M3 | delete the success-path assignment | caught (1) |
| M4 | delete the upfront `billingProvider = ""` | caught (3) |
| M5 | catch block sets `"mock"` | caught (1) |
| M6 | `String(...)` with no type check | caught (1) |
| M7 | truthy check | caught (5) |
| M8 | `isMockBilling` becomes `!== ""` | caught (1) |
| M9 | `isMockBilling` becomes a case-insensitive substring match | survives (minor, S1 still open) |
| M10 | non-OK `else` sets `"mock"` | caught (2), previously survived |
| M11 | `"mock"` set before `if (response.ok)` | caught (2), previously survived |
| M12 | upfront reset sets `"mock"` | caught (3) |
| M13 | starting value `"mock"` and upfront reset deleted | caught (4) |

### Remaining (non-blocking)

- S1: add `"Mock"` (or `"mockery"`) to the non-mock cases to pin exact-match semantics. This is the only surviving
  mutation.
- Isolation is fine. The fresh-import test uses only `fresh.*`. The other tests use the statically imported instance,
  which `resetModules` does not affect, and the `beforeEach`/`afterEach` setter resets still apply to it.
