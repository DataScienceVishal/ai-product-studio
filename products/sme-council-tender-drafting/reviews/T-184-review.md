# T-184 design review: DESIGN.md, ADR 0001, BUDGET.md rows 22-23

- Reviewer: reviewer agent, 2026-11-27. Checker for the architect's T-184 output (makers do not approve their own work).
- Under review: `DESIGN.md` (commit 24874a7), `ADR/0001-demo-architecture.md`, `state/BUDGET.md` rows 22-23.
- Checked against: `SPEC.md`, `reviews/T-183-validator.md`, the starter's backend code (`products/_starter/backend/app/*.py`), `playbooks/engineering.md`, CLAUDE.md section 10.
- No code exists yet, so there are no tests to run. Instead I ran the claims that can be checked: the parser command, the FTS query on local PostgreSQL 16, the spend-report parser on the new BUDGET rows, and every figure in section 8.

## Verdict: CHANGES

The design is careful and mostly sound. The architecture choice (starter copy, FTS, pure gate, ledger-bound eval, zero Azure) is right, the budget arithmetic is correct, and no spend can happen without Vishal's yes. But four claims about reuse do not hold against the starter code. Each one would break a slice or a bar if it were built as written:
- the nonce breaks the cache and the recordings;
- the worker deadline has no effect;
- the trial caps refuse the reservations that the design says fit;
- the export gate ignores deleted evidence.

All of them are fixable in the design without changing its direction. Required changes R1 to R8 below; the rest are suggestions.

## What I verified (evidence)

| Claim | Result | Evidence |
|---|---|---|
| `AIProvider.complete(system, user, max_output_tokens)` contract | holds | `ai.py:141-145` |
| `reserve()`/`settle()` with `feature`; cost guard, reported-model check, `ai_guard_trips` | holds | `ai.py:672-722`, `ai.py:400-422`, `models.py:131-140` |
| `store=false` on the Responses path | holds | `ai.py:468` |
| 1 MB body limit, `BodyLimit` middleware | holds | `config.py:39`, `main.py:64-104` |
| Trial caps 100k a month, 30k a day; mock and stripe tenants are "limited" | holds | `billing.py:53`, `billing.py:61`, `routes/notes.py:109-110` |
| 98,000-token global daily cap, $6.10, gpt-5-mini $2.00 in the price table | holds | `config.py:92`, `aicost.py:24`, `aicost.py:36` |
| `AI_PRICE_PER_MILLION_TOKENS` accepted for an unknown deployment name | holds | `aicost.py:54-67`, `ai.py:358` |
| 25 s AI deadline tied to the 30 s browser abort | holds | `config.py:78-82`, `config.py:128-132` |
| Rule 11 (no transaction across a model call) | holds | starter `ADR/0001-starter-foundations.md:50-52`; `reserve()` commits (`ai.py:709`) |
| `CLIENT_ROUTES` in `spa.py`, test fails on drift | holds, but see R7 (exact match only) | `spa.py:32-35`, `spa.py:74` |
| T-56 `quote_ok`, T-80 `budget.py`, T-80 p95 82.9 s | exist | `origin/p/pepr-packaging-data-pipeline/T-56:.../taxonomy.py:225`; `origin/p/restaurant-margin-copilot/T-80:.../benchmark/budget.py`; `state/BOARD.md:122` |
| FTS OR query `replace(plainto_tsquery(...)::text,'&','\|')::tsquery` | works on PG 16; stop-word-only input yields an empty query (no rows, so the gap path runs) | ran locally: `'describ' \| 'iso' \| '14001' \| ...`; `ts_rank_cd` of an ISO 9001 passage = 0.0909 (nonzero, so the must-have boost is needed, as designed) |
| `python -I -m app.tender.parse` | **fails**: `ModuleNotFoundError: No module named 'app'` (`-I` drops cwd from `sys.path`; the Dockerfile copies `app/` to `/app`, it is not installed) | ran `python3 -I -m app.textsafe` in the starter backend. **Fixed in DESIGN.md** (below) |
| BUDGET rows 22-23 vs the spend report parser | both read as $0; projection stays $23.20 | `scripts/azure_spend.py:329-349`, run on the current file → `23.2` |

### Budget arithmetic (section 8): correct
Recomputed from the section 8.2 assumptions at $0.25 / $2.00 per 1M:
- per pack: 252.5k tokens, $0.216 expected, $0.401 worst;
- E1 436.5k, $0.306 / $0.621;
- E2 612k, $0.547 / $0.997;
- E3 408k;
- E4 150k, $0.143 / $0.263;
- T2 1,048.5k, $0.853 / $1.618;
- R1 757.5k;
- totals 4,325.5k, $3.66 / $6.83.

All match within rounding. 4,326k / 98k = 44 days and 1,607k / 98k = 16.4 days are correct. One error: "about 36 days" after both cuts is 3,632k / 98k = **37** days. Fixed in DESIGN.md; ADR 0001 line 111 still says 36.

### No spend without Vishal: holds
- Section 6 and ADR decision 2 create nothing in Azure. Section 12 defers deployment to a later question.
- Q-19 is queued with no default (`state/QUESTIONS.md:158`).
- S6 refuses live calls without approval.

Weak point: see S7.

## Required changes

**R1. The nonce makes the cache and the recordings miss every time.** (DESIGN 4.3 steps 1-2, 4.4 line 128, `ai_cache` key in section 3, `ScriptedFakeAI` recorded key `sha256(user)`.)
- The nonce is 16 random hex characters per call, and it sits inside the user text.
- The `ai_cache` key hashes the user text. The recorded-fixture key is `sha256(user)`.
- So no two calls ever share a key. The cache never hits. The "cache hit costs 0 tokens" test (S3) cannot pass. R1's recordings can't be found by the offline demo, and seeding the demo tenant's cache does nothing.
- **Fix:** compute both keys from the canonical payload before wrapping: task kind, prompt version, model, system template, a JSON of the inputs with E-n numbers, and the schema. Or replace the nonce with a fixed placeholder before hashing. Say which one in 4.3.

**R2. The worker's 180 s deadline has no effect; the 20 s per-attempt timeout still applies.** (DESIGN 4.6.)
- `AzureOpenAI.complete` sends each attempt with `timeout=min(self.timeout, remaining())` (`ai.py:494`). `self.timeout` is `AI_TIMEOUT_SECONDS`, 20 s by default (`config.py:76`).
- A 60 to 80 s call therefore raises `ReadTimeout`. That is a `TransportError`, which is billed at the full output cap and never retried (`ai.py:499-503`). Every long extract or check would fail and be charged.
- **Fix:** the job runner builds its own provider instance with both `timeout` and `deadline` from worker settings. Add `WORKER_AI_TIMEOUT_SECONDS`, validated to at most 600 like `config.py:76-78`. The harness needs the same.
- **Also declare a second adapter change:**
  - reasoning effort is fixed per instance (`ai.py:340`, `ai.py:470`), but section 4.4 wants low and medium per task;
  - either add an `effort` argument to `complete()` or keep one instance per effort;
  - the "one additive change" claim (4.3, ADR decision 1) is then wrong.
- `FakeAI.complete` (`ai.py:155`) must also accept the new keyword arguments, or every fake call raises `TypeError`.

**R3. The design's reservations don't fit the trial caps it relies on, and the harness's budget path is undefined.** (DESIGN 4.3 step 3, S3 test, 8.3 R3, 8.4.)
- `reservation_estimate` counts **bytes**, plus the full output cap, plus `AI_REASONING_HEADROOM` of 1,500 (`ai.py:161-169`, `config.py:89`).
- **Extract:** a 6k-token chunk plus a 1.2k-token prompt is about 29k bytes of English. Add 6,000 output and 1,500 headroom, and the estimate is about 37k, over the 30k trial daily cap (`billing.py:53`). The S3 test "the reservation per chunk fits the 30k trial daily cap" cannot pass with these parameters.
- **Claim check:** the double-cap truncation retry (about 18k + 12,000 + 1,500) is also over 30k.
- **R3 "10 redrafts and re-checks through the app's own caps":** after one redraft settles at about 6k, the check's reservation of about 26k gives about 32k, which is over 30k. So the re-check is refused after the first redraft of the day.
- **The harness:** `run_task` step 3 calls `reserve()`. Section 1 says the harness uses "the same pipeline functions", so it would hit the same trial caps.
- **Fix:**
  - (a) make the budget step injectable: app path uses `reserve`/`settle`; harness uses the ledger and never touches `ai_usage` caps. State this in 4.3 and 8.5.
  - (b) for the app path, choose chunk size, output caps and headroom so that one reservation fits 30k. Otherwise state that live in-app extraction is not possible, and drop or resize R3. A product-local "demo" plan with a higher daily cap, still under the 98k global cap and the $6.10 line, is a reversible option. It is a decision to log, not a spend.
  - Rewrite the S3 test to match.

**R4. The export gate lets a claim through when its supporting evidence has been deleted.** (DESIGN 3 `evidence_items.deleted_at`, 4.5.)
- Evidence is soft-deleted. Claims keep their verdict and a copied `evidence_quote`.
- `export_allowed(pack, drafts, claims, signoff)` has no input for which passages are still live.
- A firm that deletes an out-of-date accreditation document can still export "supported" claims citing it. The A4 scorer ("resolves to a live passage", 8.1) would then fail on that export.
- **Fix:** pass the set of live E-ids into `export_allowed`. Any cited id that is not live blocks the export ("evidence removed; re-check"). Add this to the A6b property test, together with:
  - a check missing for the current hash;
  - a requirement added or removed after sign-off;
  - a stale `statement_version`.

**R5. Evidence text files are refused, but the SPEC requires them.**
- SPEC section 4 Must (line 44): "Evidence library upload (DOCX, PDF, text)".
- DESIGN 4.1 sniffing (line 84): "Anything else is refused."
- **Fix:** accept UTF-8 plain text for evidence uploads only: strict decode, no NUL bytes, the same size caps, and "pages" as paragraph blocks.

**R6. Slices S3, S4 and S5 are well over 45 minutes.**
- **S3** bundles about ten components: schema argument, `run_task`, cache, repair and truncation rules, `ScriptedFakeAI`, the job runner with leases, chunking, merge, cross-check and the checklist API. S4 and S5 are similar. Section 9 itself says "expect S3 to S5 each to need a second run".
- **Fix:** split each in two, each with its own tests and Done line:
  - S3a: the AI layer and job runner. S3b: extraction and the checklist API.
  - S4a: drafting. S4b: the claim check and `export_allowed`.
  - S5a: screens. S5b: docx and the Playwright e2e.
- The board tasks T-187 to T-189 need the same split. The order S1 → S2 → S3 → S4 → S5, with S6 able to run after S3, is fine.

**R7. Two starter dependencies are missing from S1 and S5.**
- **(a) Account export.** `routes/account.py:15,31,37-38` imports and exports `Note`. Removing `Note` breaks it, and the data export must cover the new customer-content tables (DATA.md retention, UK GDPR). Add this to S1.
- **(b) Dynamic SPA routes.** `CLIENT_ROUTES` is an exact-match set (`spa.py:74`). A deep link like `/packs/<id>` is served with HTTP 404. Choose one of these and state it in section 5:
  - static client routes with query ids (`/pack?id=`);
  - a reviewed prefix-pattern change to `spa.py`.

**R8. The `-I -m` parser command (fixed).** I changed DESIGN 4.1 to a standalone script started by absolute path, with an empty environment and limits set inside the child. The architect should confirm the wording. See "Fixes applied".

## Suggestions (not blocking)

**S1. Tenancy details:**
- the starter's `_scoped(me)` takes a request user (`routes/notes.py:46`), so workers need `_scoped(model, tenant_id)`;
- `retrieved_ids` and `cited_ids` are `int[]` that no foreign key can protect; say they hold tenant-local `display_no` and that every lookup filters `tenant_id`;
- `ai_tasks.target_id` refers to different tables, so it can have no foreign key; say how each kind resolves it, scoped by tenant;
- make `signoffs.reviewer_user_id` a composite foreign key to `users(tenant_id, id)`, which needs `UNIQUE (tenant_id, id)` on `users`.

**S2. Gate edge cases:**
- check limits against the current confirmed `requirements.word_limit`, not `word_limit_snapshot`;
- pre-register a rule for page limits ("2 sides of A4"): words per side, or a flag for a human;
- decide whether open `[NEEDS FIRM INPUT]` markers block export or only warn;
- record `checked_text_sha256` and `checked_at` on `drafts`;
- build the docx from the same in-memory rows that were passed to `export_allowed`, so a write between the gate and the build can't slip in;
- an uncited factual claim should be `unsupported` explicitly.

**S3. Prompt injection:**
- in `claimcheck`, the draft text can carry injected tender text, so put it inside a DATA block too;
- the unchecked-sentence detector misses `commitment` sentences with no digits or capitalised runs (for example "we always respond within agreed timescales"); list this as a known gap next to A6a.

**S4. Parser:**
- add `RLIMIT_FSIZE` and `RLIMIT_NOFILE`;
- "fewer than 30 characters on any page" also refuses divider or cover pages, so require little text **and** an image object on the page;
- pypdf, python-docx and python-multipart (FastAPI needs it for `UploadFile`) are not in `backend/requirements.txt`; add them with hashes in S2;
- add hypothesis to the dev requirements in S4.

**S5. Job runner:**
- extend the lease per model call: a task with a repair, a shorten and a double-cap retry can make 4 calls of up to 180 s each, which exceeds the 10-minute lease;
- workers must apply the same gates as `routes/notes.py:99-120`: `has_access`, email verification, the AI rate limit and `AISlots`;
- keep worker threads off in tests and drive them by hand;
- "taken over on the next poll" should say whether workers poll the table or the browser triggers the takeover.

**S6. Worst case vs the sub-caps:**
- worst figures leave out the 1,500-token reasoning headroom per Responses call (`ai.py:342,466`) and the retries, so set the headroom to 0 in the harness or add it to the worst case;
- even without it, worst cases pass the proposed sub-caps: tuning T1+T2+T3 = $2.68 > $2.00; R1+R2 = $1.60 > $1.40; total $6.83 > $6.00;
- the ledger still holds the hard cap, but the design should say which phase gets cut short first;
- Q-19's context line in `state/QUESTIONS.md:160` says "worst case inside $6", which is not accurate: the $6 cap binds before the worst case is reached. The Lead should correct it, since Vishal decides on that text.

**S7. Approval guard.** `TENDER_EVAL_SPEND_APPROVED=1` is an environment variable any run can set. Prefer a committed `eval/budget.json` that names Q-19, the answer date and the caps; the ledger refuses to run without it. That makes the approval auditable.

**S8. BUDGET row 22.** The spend parser's `listed_names` (`scripts/azure_spend.py:305-317`) reads that row's names as `build`, `local`, `caj-tender-migrate/-purge/-cancels`, and so on. So if the app is deployed, `ca-tender` would show as unlisted. That fails safe, but split it into one row per resource when deployment is approved.

**S9. Eval integrity.** `requirements` keeps `origin=model` plus `edited_by` but no copy of the original model output. Store the model's JSON (or keep the proposed row unchanged) so "the eval compares the output before any edit" holds if anyone ever scores a tenant's data.

## Fixes applied to DESIGN.md (small, unambiguous)
1. **4.1 Sandbox.** `python -I -m app.tender.parse` became a standalone script by absolute path (`python -I /app/app/tender/parse_worker.py`) that imports no `app` code. It runs with an empty environment and sets its limits with `setrlimit` inside the child, not through `preexec_fn`. Reason: the original command fails (verified), and the child would otherwise inherit `DATABASE_URL` and the AI settings.
2. **Section 3, `source_documents`.** Added the `page_mode` column, which the `document_pages` note referred to but the column list did not include.
3. **8.4.** "about 36 days" became "about 37 days", with the arithmetic shown. ADR 0001 line 111 still says 36; the architect should align it.

## Next
The architect addresses R1 to R7, plus ADR line 111, and updates the board tasks T-187 to T-189 for the split. Then re-review. I expect the re-review to be quick if the fixes follow the ones given above.

## Re-review (2026-11-27, after commit e213623; board re-cut in 90eb49c)

### Verdict: PASS

I reviewed only the changes (`git diff 62552c3 e213623`, DESIGN section 13) and how they interact with the starter code.

| Finding | Status | Evidence |
|---|---|---|
| R1 nonce vs cache | fixed | Both the cache key and the recording key come from the canonical payload before wrapping (DESIGN section 3 `ai_cache` row; 4.3 `run_task` step 1; the `ScriptedFakeAI` recorded path). An S3 test asserts a hit across different nonces |
| R2 worker timeout and effort | fixed | All three adapter changes are declared (DESIGN 4.3 items 1-3; ADR decision 1). The worker instance gets both `timeout` and `deadline`, which addresses `ai.py:494`. Per-call `effort` replaces the per-instance setting at `ai.py:340,470`. The fakes accept the new keyword arguments. An S3 test checks that the worker uses 180 s |
| R3 caps and harness budget | fixed | The budget port (`AppBudget` around `reserve`/`settle`; `LedgerBudget` never writes `ai_usage`), plus an S9 test. App-path extraction is cache or fake only. The double-cap retry runs in the harness only. Headroom is 0 in the harness (8.5). Arithmetic checked: check reservation 5.6k + 3k + 4k + 6,000 + 1,500 = 20.1k; draft about 16.4k + 5.5k = 21.9k; one pair fits 30k (`billing.py:53`) |
| R4 deleted evidence | fixed | `export_allowed(..., live_evidence_ids, statement_version)` (DESIGN 4.5). The S6 property test and an S8 export test cover it |
| R5 text evidence | fixed | DESIGN 4.1 sniffing; an S2 test |
| R6 slices | fixed | Nine slices with their own tests and Done lines, in order, with S9 parallel after S3. The board has T-185 to T-196 to match (`state/BOARD.md:12-23`) |
| R7 account export, SPA routes | fixed | S1 replaces `routes/account.py`'s `Note` export. Static routes with query ids work with the exact-match `spa.py:74`, so `spa.py` stays unchanged |
| ADR "36 days" | fixed | ADR decision 7 now says 37 days (3,632k / 98k) |

### Small fixes I applied to DESIGN.md in this pass
1. **4.3, R3 demo moments.** "the 49k trial pool allows about 3 a day" now says 2 to 3 pairs, with the arithmetic. After two settled pairs of about 13.6k each, a third draft reservation of about 22k reaches the 49k pool (`ai.py:701`).
2. **4.3, draft reservation.** "(about 16k bytes)" now says "of input in all", so it no longer reads as 8 × 1.4k.
3. **S6.** "cited passages only on the app path" now says the input is the same in the app and in the harness. The old wording suggested the A6a eval might measure a different checker input than the product uses.

### Notes for slice reviews (not blocking)
- **Draft-and-check pair near the cap.** At the maximum passage size (400 words, about 2.4k bytes), a draft reserves about 29.9k. A pair then lands at about 30.1k, just over the 30k cap. This fails closed with the starter's refusal message. The S5 test should use maximum-size passages, or the app path should cap k so that the worst case fits.
- **Signature changes.** `build_provider(settings, timeout=, deadline=)` changes the starter's signature (`ai.py:589`). Keep the defaults so that `main.py` and the existing tests still pass.
- **Open suggestions.** My earlier suggestions S2 (page limits, open gap markers at export), S3 (the detector's blind spot for commitment sentences), S4 (parser rlimits, image-only rule) and S8 (splitting the BUDGET row at deploy time) remain open for the slice reviews, as the architect noted.
