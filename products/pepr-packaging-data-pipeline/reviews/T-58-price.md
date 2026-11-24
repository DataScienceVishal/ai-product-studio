# Review: T-58 price correction (commit ea0f2e0, branch p/pepr-packaging-data-pipeline/T-56)

Reviewer, 2026-11-24. Scope: `git show ea0f2e0` (budget.py, score.py, tests, benchmark/README.md, NEXT.md), plus every other code path that touches price or the ledger. No model call was made; `T56_SPEND_APPROVED` was never set.

## Verdict: PASS

The repricing is correct, it fails closed, and it now lives in one place. No code path still prices at 15/120, and no code path uses the stored `usd` value to make a decision. The tests would catch a revert of each of the three changes. The suggestions below are small: docs and hygiene. None of them blocks the merge.

## Evidence

- Tests: `/usr/bin/python3 -m pytest -q extractor/tests benchmark/tests` gives **148 passed in 8.30s**.
- I recomputed the real ledger (`results/ledger.jsonl`, 5 rows) through the code (`Budget` and `score.read_ledger_cost`):
  - S901 0.1385, S902 0.5021, S903 0.4451, S904 1.0779, S905 0.9279. Total **USD 3.0915**, 25,805 tokens. This matches NEXT.md.
  - Left under the cap: 12 - 3.0915 = **USD 8.9085**.
  - `preflight(b, 30, extract.MAX_OUTPUT_TOKENS=6000)` raises `pre-flight: USD 8.91 left, need 11.16 (short by 2.25)`. That is 30 x 0.316 = 9.48, plus a worst case of 20,000 x 30/1M + 6,000 x 180/1M = 0.60 + 1.08 = 1.68. The test set has 30 PDFs. The builder's figures are correct.
- Grep for price and usd use across `*.py` outside the tests:
  - `budget.usd()` is the only price formula. `score.py` imports `extractor.budget`.
  - `extract.py:158` (`pred.usage.usd`) and `run.py:90` print the price only; they decide nothing.
  - `run.py:26` reads `float(e["usd"])` only as a check that the row parses (see S2). It never uses the value.
  - `score.py` builds pass mark 5 only from `read_ledger_cost`, not from `pred.usage.usd`.

## Correctness checks

- **Estimated 5xx rows:** `providers.py:153` records `(worst_in, max_output_tokens, estimated=True)`, so those rows carry tokens and are repriced at 30/180. Correct.
- **Timeouts and unreadable responses:** `ProviderError(..., worst_in, max_output_tokens, may_have_run=True)`, and `extract.py` records those tokens. Repriced correctly.
- **Non-completed responses** with billed tokens are recorded with their real tokens, so they are repriced too.
- **Rows missing token fields:** `entry_usd` raises `KeyError`, so `Budget` start-up and `score.read_ledger_cost` fail closed. Before this commit, `read_ledger_cost` used `e.get("usd", 0.0)`, which would silently count a bad row as USD 0, so this is an improvement. In `Budget` this was already the behaviour, through `int(e["input_tokens"])`.
- **Mixed old and new rows:** every row is repriced from its tokens at the current constants. The stored `price_in`/`price_out` are informational only. That matches the docs.
- **Conservatism:** cached input tokens are billed at the full input price, and output already includes reasoning. Both lean conservative, which is right for a cap.

## Critical issues

None.

## Suggestions

S1. **The governing pre-registered document still says 15/120.** `benchmark/KILL_TEST_AMENDMENT.md:12` (item 4) says: "Price basis: USD 15 per 1M input and USD 120 per 1M output ... The GBP 0.25 per sheet check is computed on that basis." The code now computes pass mark 5 at 30/180. The change only makes the test stricter, so it is not goal-post moving. But the kill-test document and the code now disagree. Append a dated correction under item 4 that points to T-58 and DECISIONS line 168. Do not rewrite the original text.

S2. **The supplement gate still requires a `usd` field that `Budget` no longer needs.** `run.py:26` checks `float(e["usd"])`. A row without `usd` is now valid for `Budget`, but the gate rejects it. It fails closed, so this is harmless. For consistency, validate with `budget_mod.entry_usd(e)` instead, which checks what the guard actually reads.

S3. **NEXT.md hand-off conflicts with the latest decision.** The new section says "Q-12 (raise cap to USD 20) is still needed". DECISIONS line 169, from the same run, changed the Q-12 recommendation to "add a mini deployment and amend the test before running". The Run e08c section also still tells the next run to raise the cap and run the test set when Q-12 is answered A. Update NEXT.md so the next run does not act on the old recommendation.

S4. **NEXT.md line 42 still describes the guard as pricing "at USD 15/120 per 1M".** Mark it as superseded, or change it to 30/180.

S5. **One test comment is wrong.** In `test_score_cost_check_uses_tokens_at_current_price`, the comment "a sheet whose stored usd passes 0.316 but whose repriced cost fails" sits on the `m.jsonl` case. That row is 0.18 stored and 0.27 repriced, so it passes both ways. Only the `n.jsonl` case (0.228 to 0.342) matches the comment. Move the comment, or drop the `m` case.

S6. **Two test gaps.** There is no test with a mixed ledger (old rows without `price_in`, new rows written by `record()`, then a fresh `Budget`). There is also no test that a row missing `input_tokens` makes `read_ledger_cost` raise instead of counting 0. Both behaviours are correct today; tests would pin them.

S7. **Hygiene.**
  - `Budget.record` adds the rounded `entry["usd"]`, while start-up adds the unrounded `entry_usd`. The difference is at most 5e-7 per row, which does not matter. Using `entry_usd(entry)` in both places would remove the inconsistency.
  - `PER_SHEET_USD` (budget.py) and `USD_PER_SHEET_MAX` (score.py) both hold 0.316. Now that score.py imports budget, import this one too.

## Not verified

I did not fetch the two price sources. The 30/180 figure was taken from the brief and from state/BUDGET.md, which cite them.
