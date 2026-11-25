# Review: p/_starter/T-85-mock-case (569d937)

**Verdict: PASS**

## Summary
One test-only change: `products/_starter/frontend/src/api.test.ts:194-199` adds an `it.each` over
`"Mock"`, `"MOCK"`, `" mock"`, `"mock "`, `"mockery"`, `"not-mock"`, `""`. Each case sets the flag to mock
first, so a failure can only come from `loadClientConfig` wrongly keeping it on. This closes the T-84 review item.
No product code changed.

## Evidence
- `npx vitest run` on the branch: 6 files, **173/173 pass**.
- Mutation runs of `isMockBilling` (`src/api.ts:30`), done in a scratch copy and not in the checkout:
  | Mutant | New tests failing |
  |---|---|
  | `.trim().toLowerCase() === "mock"` | 4 (Mock, MOCK, " mock", "mock ") |
  | `.includes("mock")` | 4 (" mock", "mock ", mockery, not-mock) |
  | `.toLowerCase() === "mock"` | 2 (Mock, MOCK) |
  | `.trim() === "mock"` | 2 (" mock", "mock ") |
- The existing positive cases (lines 173 and 179, `billing_provider: "mock"` turns mock on) still pass, so the stricter checks don't hide a broken happy path.

## Critical issues
None.

## Suggestions (non-blocking)
- The `it.each` line is about 180 characters long. Wrapping the array would make it easier to read, but it matches the style of the neighbouring non-string `it.each`.
- `""` duplicates the fail-closed default. That's harmless.
