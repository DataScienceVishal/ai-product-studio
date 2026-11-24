# Review: p/_starter/T-15-scanner (bc83c9c)

Reviewer: reviewer agent, 2026-11-24. Diff: `git diff main...origin/p/_starter/T-15-scanner` (README.md, backend/tests/test_spa.py, infra/main.bicep).

## Verdict: CHANGES

## Summary

- Tests: backend **422 passed, 1 skipped** (59 s, Postgres 16, fresh worktree). That matches the README's new count. The frontend is unchanged, so I did not re-run vitest; the builder reports 114 passed.
- The scanner work works for the forms it tests, and the existing unreadable cases still get flagged. But the new `PAGES[path]` resolution **can pass silently** for several ordinary ways of writing the object literal. That breaks the rule the test exists for: never pass silently.
- The README "Calls per day" note and the Bicep comment get the inputs right (1,200 + 1,500 = 2,700; trial share 0.5). The conclusion drawn from them is wrong, because reservations are settled down to actual usage.

## Critical issues

### C1. `PAGES[path]` resolution misses routes silently (test_spa.py, `lookup()` in `scan_routes`, `_KEY_ENTRY`)

`lookup()` treats the object as fully read when every key `_KEY_ENTRY` found starts with `/`. Any entry `_KEY_ENTRY` can't see is dropped with no flag. I checked each case below by calling `scan_routes` on the branch:

| Source | Result | Missed route |
|---|---|---|
| `const PAGES = {\n "/a": A, // home\n "/b": B };` | `({'/a'}, [])` | /b |
| `const PAGES = { // pages\n "/a": A,\n "/b": B };` | `({'/b'}, [])` | /a |
| `const PAGES = { "/a": A, [ROUTES.b]: B };` | `({'/a'}, [])` | /b |
| `const PAGES = { ...MORE, "/a": A };` | `({'/a'}, [])` | everything in MORE |
| `const PAGES = { "/a": A, "/b"() { return B; } };` | `({'/a'}, [])` | /b |
| `const PAGES = { "/a": A };\nPAGES["/b"] = B;` | `({'/a'}, [])` | /b |
| a second `const PAGES = {...}` in another scope (last one wins) | `({'/a'}, [])` | /b |

Each row ends with `return PAGES[path];`. Every row has `other == []`, so `test_client_routes_match_the_frontend_router` would pass while a page is missing from `CLIENT_ROUTES`, and a refresh on that page would 404 in production. A comment between entries is very common in TSX. `[ROUTES.x]: Page` is the exact combination this change invites people to write.

**Fix:** parse the object's top-level entries instead of searching for keys inside it. Strip `//` and `/* */` comments, split on commas at depth 0, and require **every** entry to match `^\s*(["'`])(/[^"'`$]*)\1\s*:`. If any entry is a spread, computed key, method, shorthand or bare key, return the lookup as unreadable. Also treat these as unreadable for any name being resolved: a second declaration of the name, or any assignment to it (`NAME[...] =`, `NAME.x =`, `NAME =`). Add every row of the table above as a test that must report `other`.

### C2. README "Calls per day" and the main.bicep comment misstate how the cap works (README.md, the new paragraph; infra/main.bicep lines 62-63)

The README says the cap "admits `cap / reservation` calls however short the real answers are", and Bicep says "100,000 admits only about 33 calls a day". In the code, `reserve()` (app/ai.py:453) writes the estimate, and `settle()` (app/ai.py:491) **overwrites it with the actual tokens** after the call. `tokens_today_all_tenants` adds up the settled rows. So about 33 is the floor: you get it only if every call uses its whole budget or the calls all run at once. Calls one after another with short answers (say 600 tokens actual) fit roughly (100,000 - 3,000) / 600 + 1, about 160 a day. The real sizing facts are different:
1. A call needs about 3k of headroom left under the cap, so the last ~3k of each day's cap can never be used by a full call.
2. The cap only binds on concurrent or worst-case usage.

Three smaller inaccuracies in the same paragraph:
- **"About 300 input" is a floor, not typical.** `SUMMARY_SYSTEM` alone is 287 bytes and the `<note>` wrapper is 17, so an empty note is already about 304. A normal 1-2 KB note makes the reservation 4-5k. The largest note (20,000 chars; up to about 80 KB with multibyte UTF-8) reserves 23k-83k, which is more than the 30k trial daily cap.
- **The headroom only applies to the Responses API.** The default is `azureOpenAiApi = 'auto'`, which picks chat unless the endpoint ends in `/openai/v1/responses`. On chat the reservation is 1,200 + input. The worked example should say which API it assumes.
- **"33 for all customers, trials half" doesn't describe today's deployment.** `LIMITED_PROVIDERS = {"mock", "stripe"}` (routes/notes.py:27) makes **every** tenant `limited` until selling is unlocked. All calls therefore go to the trial pool (50k), and each trial tenant also has the 30k daily cap from `PLANS["trial"]`.

**Fix:** rewrite it as "the cap admits at least `cap / reservation` calls (all running at once, or each using its full budget); reservations are settled to actual usage, so short answers leave room for more; a call is refused once less than its reservation is left." Give the reservation as `287 + note bytes + 17 + 1,200 (+1,500 on Responses)`. Add that until `unlock selling`, every tenant draws from the trial half. Correct the Bicep comment to match, or just point it to the README.

## Suggestions

- **S1. `ROUTES.a` resolves even when more expression follows.** `path === ROUTES.a + "/sub"` and `path === ROUTES.a.toLowerCase()` both give `({'/a'}, [])`, and the rest is replaced by a blank. The literal form has the same gap on main: `path === "/a" + "/sub"` gives `{'/a'}`. These usually show up as a mismatch rather than a silent pass, but add a lookahead such as `(?=\s*(?:\)|&&|\|\||\?|;|:|,|$))` after the comparand to the literal and member patterns, and add tests.
- **S2. Nested objects leak into the lookups.** `const ROUTES = { x: { a: "/a" } }` resolves `ROUTES.a` to `/a`, and `{ "/a": { "/b": B } }` reports `/b`. Parsing entries only at depth 0 (C1) fixes both.
- **S3. Some membership checks aren't flagged.** `SET.has(path)` and `[...].indexOf(path)` aren't in `_OTHER`. Today `PUBLIC.has(path)` in App.tsx is an auth check, not routing, but routing written as `if (ROUTES_SET.has(path))` would be invisible. Consider flagging `.has(path)` unless the line is on an allow-list.
- **S4. Make the regression guard prove the form-by-form claim.** Its docstring says "each route comes from exactly one form". Parametrise it so that removing each form's line drops exactly that route. That turns the claim into an assertion.
- **S5. Quote tracking in `_object_literals`.** An apostrophe in JSX text or a comment (`<p>Don't</p>`) switches the brace walker into string mode. Today that fails loud (the object isn't found, so `PAGES[path]` gets flagged). Stripping comments first would cut down the noise.

## Checked and fine

- The README test count (422/1) matches my run.
- Old unreadable cases (`pages.main[path]`, `x === path`, `!==`, `==`, `!=`) are still flagged. Unknown objects, missing members, non-route values and computed values are flagged too.
- The current App.tsx uses only `path === "/x"` and scans clean.
- The change is test-only plus docs and comments. It has no runtime, security or performance effect.

---

# Re-review: 69c1971 (fixes on top of bc83c9c)

Reviewer: reviewer agent, 2026-11-24. Delta: `git diff bc83c9c 69c1971` (README.md, test_spa.py, main.bicep).

## Verdict: CHANGES (narrow)

## Tests

Backend on 69c1971 in the scratch worktree: **449 passed, 1 skipped** (59 s). That matches the README's new count. The frontend is unchanged, so I did not re-run vitest; the builder reports 114 passed.

## What is fixed

- **C1, all seven original cases.** Spread, computed key, method, shorthand, bare key, later assignment, `Object.assign`, duplicate declaration and reassignment are now all reported as unreadable, and each has a parametrised test. ROUTES gets the same duplicate and assignment rules. Nested keys are no longer read.
- **S1.** A compared value must now end at the literal (`_END`, plus the operator check in `literal()`). `+ "/sub"` and `.toLowerCase()` now fall through to unreadable, with tests.
- **S3.** `.has`, `.indexOf` and `.includes(path)` are flagged.
- **S4.** The guard is now parametrised so that removing each form drops exactly its route.
- **C2.** The README now says the cap is a floor, explains settle(), gives the reservation formula as 287 + bytes + 17 + 1,200 (+1,500 on Responses only), notes that `auto` picks chat, covers the 20k-character note, and says LIMITED_PROVIDERS puts every tenant in the trial half. The Bicep comment is rewritten to match. I checked all of it against app/ai.py, routes/notes.py and config.py.

## Choosing to resolve comment-separated objects

Resolving them is acceptable in principle. Comments carry no routes, so a correct, string-aware stripper loses nothing, and flagging every commented object would push developers to delete useful comments. The catch is that the stripper and the entry splitter are now the places a route can vanish. They need to fail loud when they are unsure, and today they don't (R1).

## Critical issues

### R1. Quote and comment heuristics can still hide a route silently (test_spa.py, `_split_top_level`, `_object_literals`, `_strip_comments`)

I ran `scan_routes` on 69c1971 for each source below:

| Source | Result | Missed route |
|---|---|---|
| `const PAGES = {\n "/a": () => <p>Don't</p>,\n "/b": () => <p>It's</p>,\n "/c": C };` + `return PAGES[path];` | `({'/a','/c'}, [])` | /b |
| `if (x) return <p>see http://x</p>; if (path === "/b") go();` | `(set(), [])` | /b |
| `if (/a\//.test(x) \|\| path === "/b") go();` | `(set(), [])` | /b |
| `const p = s.replace(/\/*$/, "");` then routes on later lines | `(set(), [])` | every later route |

Why each one happens:
- **Row 1.** `_split_top_level` (and the brace walker in `_object_literals`) treats an apostrophe in JSX text as opening a string. Everything up to the next apostrophe becomes one string, so `"/b": ...` merges into the `/a` entry. Every remaining entry still starts with a quoted route, so the lookup is accepted. JSX text with "Don't" or "It's" is ordinary UI copy, and an inline `() => <Page/>` value is exactly the style the PAGES form invites.
- **Rows 2 and 3.** `//` inside JSX text or a regex literal is taken as a line comment, and the rest of the line is thrown away.
- **Row 4.** `/*` inside a regex (a common trailing-slash trim) starts an unterminated block comment, so the rest of the file is thrown away. That usually shows up loudly as an equality mismatch, but only by luck: if the only route after it is the new one, the test passes.

**Fix (fail loud rather than parse JS properly):**
1. In `_split_top_level` and the `_object_literals` walker, end `'` and `"` strings at a newline, the same as `_strip_comments` already does.
2. In `lookup()`, count every `(["'`])/[^"'`$]*\1\s*:` occurrence in the object's whole text. If that count is not equal to the number of top-level entries, report the lookup as unreadable. This catches merged entries whatever caused them, and it also flags nested route-keyed objects, which is fine.
3. In `_strip_comments`, treat two cases as unreadable instead of silently resolving them: an unterminated `/*`, and a `//` or `/*` that is neither first on its line nor preceded by whitespace when the text it removes contains `path`. Commented-out route lines (`// if (path === ...)`) still count as comments, so the existing test keeps passing.

Add the four rows above as tests that must report `other`.

## Suggestions

- **S6. The README worked example is off by one.** 287 + 1,000 + 17 + 2,700 = 4,004, and 100,000 / 4,004 = 24.97. The 25th call is refused, because 24 x 4,004 + 4,004 = 100,100, which is over 100,000. Say "at least 24", or round the note to 990 bytes so it comes out at exactly 4,000.
- **S7. The PUBLIC allow-list is a suffix match.** `(?<!PUBLIC)\.has(path)` also lets through `NOTPUBLIC.has(path)` and `MY_PUBLIC.has(path)` (both give `(set(), [])`). Anchor it as `(?<![\w$])PUBLIC\s*\.\s*has`. One way: drop the lookbehind and remove an exact `\bPUBLIC\.has\(path\)` before the `_OTHER` scan.
- **S8. Assignment through an alias isn't caught.** `const R = ROUTES; R.a = "/z"` still resolves `ROUTES.a` to `/a`. This is unlikely in practice; one option is to treat any bare reference `= ROUTES` or `(ROUTES` outside member access as unreadable.
- **S9. Imports reordered.** In test_spa.py, `from fastapi.testclient import TestClient` was moved below the first-party `app` imports. That is not standard isort order and it is unrelated churn. Revert it.

## Checked and fine on 69c1971

- The original C1 table now flags every row except the two comment rows, which now resolve correctly to `{'/a','/b'}`.
- Template-literal computed keys, `PAGES[path] ?? NotFound`, `path === ROUTES.a ? ... : ...` and `path === await f()` behave correctly.
- App.tsx still scans clean.
- No runtime code changed.

---

# Re-review 2: b26c0c7 (fixes on top of 69c1971)

Reviewer: reviewer agent, 2026-11-24. Delta: `git diff 69c1971 b26c0c7` (test_spa.py, README.md).

## Verdict: CHANGES (one hole left in the R1 fix)

## Tests

Backend on b26c0c7 in the scratch worktree: **458 passed, 1 skipped** (60 s). That matches the README. The frontend is unchanged; the builder reports vitest 114 passed.

## What is fixed

- **R1, all four sources.** Each is now flagged, with must-flag tests.
  - Strings now end at a newline in the splitter and the brace walker.
  - The lookup now requires the number of `"/route":` keys in the object to equal the number of top-level entries. Nested route-keyed objects are reported as unreadable.
  - An unterminated `/*` is flagged, and so is a comment marker mid-line, not after whitespace, that removes text containing `path`.
- **S6.** The README now says "at least 24 (100,000 / 4,004)", which is correct. The sum before it still says "= 4,000"; see S10.
- **S7.** Only the exact name `PUBLIC` is allowed, enforced by the `_PUBLIC_CHECK` lookbehind (`(?<![\w$.])`). Tests cover `MY_PUBLIC`, `NOTPUBLIC`, `x.PUBLIC` and `PUBLIC2`.
- **S8.** The alias limitation is documented in a comment. Accepted.
- **S9.** The import order is restored.

## Fresh adversarial sources

I ran `scan_routes` on b26c0c7 for each source below.

| Source | Result | OK? |
|---|---|---|
| one line: `{ "/a": () => <p>Don't</p>, "/b": () => <p>It's</p> }` | flagged | yes |
| a backtick in JSX text inside a PAGES value | flagged | yes |
| `/'/g` regex inside a PAGES value | flagged | yes |
| an escaped quote inside a value string | flagged | yes |
| ROUTES with an apostrophe in a trailing comment | `{'/b'}` (correct) | yes |
| `LIST.find((r) => r.path === path)` | flagged | yes |
| `{\n "/a": () => <p>Don't</p>,\n ...MORE,\n "/c": C }` + `PAGES[path]` | `({'/a','/c'}, [])` | **no**: MORE's routes are missed |
| the same with `[ROUTES.b]: B` or `home: H` on the swallowed line | `({'/a','/c'}, [])` | **no**: /b is missed |
| `return <p>a // b</p>; if (path === "/b") go();` | `(set(), [])` | no, but contrived (S11) |
| `PAGES.get(path)` (Map routing), `path in PAGES` | `(set(), [])` | no; this gap was already on main (S12) |

## Critical issue

### R2. A misread apostrophe can still swallow a non-route entry (test_spa.py, `lookup()` / `_split_top_level`)

The route-key count only notices when the swallowed line holds a **route key**. Suppose an apostrophe in JSX text runs to the end of the line, the comma there is hidden, and the next line is a spread, a computed key or a bare key. That line merges into the previous `"/a": ...` entry. Every remaining entry still starts with a quoted route, and the count of route keys still equals the count of entries. So the lookup is accepted and the swallowed routes are missed with nothing flagged.

**Fix (small):** a `'` or `"` string closed by a newline instead of its own quote is, by definition, a misread. Have `_split_top_level` (or the walker in `_object_literals`) report when that happens inside the object body, and make `lookup()` treat that object as unreadable. ROUTES members are already safe, because a merged entry fails `_STR_ENTRY` and the member then goes unresolved and gets flagged. Add the spread, computed and bare variants above as must-flag tests.

## Suggestions

- **S10.** README: "287 + 1,000 + 17 + 2,700 = 4,000" should be "= 4,004", so it agrees with the 100,000 / 4,004 next to it.
- **S11.** A `//` preceded by whitespace in JSX text (`<p>a // b</p>`) is still treated as a comment, so a route later on the same line is missed. This is rare. You could extend the mid-line check to any `//` that isn't first on its line, when the removed text contains `path`.
- **S12.** This was already true on main and is out of scope for T-15. `.get(path)` (Map-based routing) and `path in X` are not in `_OTHER`. Adding `\.\s*get\s*\(\s*path\s*\)` and `\bpath\s+in\b` is cheap and in keeping with "fail loud". General `fn(path)` can't be flagged without noise, so it stays a documented limit of a heuristic scanner.

## Checked and fine on b26c0c7

- Every earlier must-flag case still fails loud, and the comment-object cases still resolve.
- App.tsx scans clean.
- The README AI-cap numbers are correct apart from S10.
- No runtime code changed.

---

# Re-review 3: e685f20 (fixes on top of b26c0c7)

Reviewer: reviewer agent, 2026-11-24. Delta: `git diff b26c0c7 e685f20` (test_spa.py, README.md).

## Verdict: PASS

## Tests

Backend on e685f20 in the scratch worktree: **466 passed, 1 skipped** (62 s). That matches the README. The frontend is unchanged; the builder reports vitest 114 passed.

## What is fixed

- **R2.** `_split_top_level` now returns a `misread` flag whenever a `'` or `"` string is closed by a newline. `lookup()` refuses an object that has that flag. I re-ran my R2 sources on e685f20: an apostrophe line followed by a spread, a computed key or a bare key is now flagged, and the builder added parametrised must-flag tests, including the spread-plus-comment variant. ROUTES members were already safe, because a merged entry fails `_STR_ENTRY`.
- **S10.** The README sum now reads 4,004, which matches 100,000 / 4,004 = 24.97, so at least 24 calls.
- **S11.** Any `//` or `/*` that isn't first on its line is flagged if the text it removes contains `path`. `<p>a // b</p>; if (path === "/b")` is now flagged.
- **S12.** `.get(path)` and `path in X` are flagged, with tests.

## Fresh adversarial sources

I ran `scan_routes` on e685f20 for each source below.

| Source | Result | Verdict |
|---|---|---|
| A Prettier-style multi-line PAGES (`Record<string, () => JSX.Element>`, JSX values) | `({'/a','/b'}, [])` | correct |
| A multi-line PAGES value with JSX copy `<p>We're here</p>` | flagged | fails loud (a false positive, but safe) |
| A lone backtick in JSX text, with a later backtick | flagged | fails loud |
| A ternary chain with a trailing comment; an `else if` chain | resolved correctly | correct |
| `<p>The path in the URL</p>` | flagged (`path in`) | fails loud (a false positive, but safe) |
| **A one-line object with two apostrophes on the same line hiding a non-route entry:** `{ "/a": () => <p>Don't</p>, ...MORE, [X]: () => <p>It's</p>, "/c": C }` | `({'/a','/c'}, [])` | silent pass, but **not realistic here** (F1) |

The one silent pass needs a whole PAGES object on a single line, with JSX text containing two apostrophes and a non-route entry between them. Prettier splits objects like that across lines, and once the object is multi-line each apostrophe closes at its newline and sets the misread flag. App.tsx today uses only `path === "/x"`, which scans clean. Under the coordinator's bar (hold PASS back only for realistic silent passes), this is a follow-up.

## Follow-ups (not blocking)

- **F1.** One-line objects with paired apostrophes (above). Possible fix: also count top-level entries with quotes ignored (split on commas at depth 0, counting brackets only). If that count differs from the quote-aware count, report the object as unreadable.
- **F2.** Fail-loud false positives (an apostrophe in a PAGES value, `path in` in JSX text) will now and then make a developer restructure code. The assertion message in `test_client_routes_match_the_frontend_router` could name the likely causes, such as "JSX text apostrophes inside a PAGES object, or a comment marker mid-line", so the fix is obvious.
- **F3.** The S8 alias case and general `fn(path)` routing remain documented limits of a regex scanner. If routing ever outgrows `path === "/x"`, replace the heuristic with a TypeScript AST check, for example a small `tsc`/esbuild script in the frontend test suite.

## Summary across the four rounds

- Every silent-pass case found in rounds 1-3 (comments, computed keys, spread, methods, shorthand, mutation, duplicates, concatenation, nested objects, JSX apostrophes, `//` and `/*` inside regexes or JSX text, `.has`, `.get`, `path in`) is now either resolved correctly or flagged, and each has a test.
- The README and Bicep text on the AI cap now matches app/ai.py `reserve()`/`settle()`, routes/notes.py and config.py.
- The change is test-only plus docs and comments, so it has no runtime, security or performance effect.
