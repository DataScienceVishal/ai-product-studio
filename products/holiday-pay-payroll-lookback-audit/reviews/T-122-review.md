# T-122 review: mapper spend cap, size limits, https-only, no redirects

Branch `p/holiday-pay-payroll-lookback-audit/T-122` at 206521e, diffed against `origin/main` (merge base eee655f).
Changed: `mapper/mapper.py`, `mapper/run.py`, `mapper/README.md`, `tests/test_mapper.py`. `mapper/prompt.py` is untouched.

**Verdict: PASS**

## Summary

This change fixes M-2 and L-3 from `reviews/T-120-security.md`. It does not affect the kill-test one-shot and pre-registration rules:

- `prompt.py` is not changed, and `PROMPT_SHA256` is still `ae175fa9c2fa89f244dba58854abe9ea0739d86ea35cfe9a917b746b88a4a5ed`. A new test pins this value.
- The cap is not part of `config_sha256`, so a re-run after a no-answer attempt with the same config is still allowed.
- Every guard runs before anything is written to disk. The `--max-usd` and `--allow-over-cap` checks, the endpoint scheme check in `from_env`, `preflight()` and `set_spend_cap()` all run before `os.makedirs`, before `run.started` is written and before anything is appended to `attempts.jsonl` (`run.py` main, in that order). The only earlier disk access is reading `live_run_exists` and `attempts.jsonl`. Tests check that `run.started` is absent after a refusal.
- A 3xx surfaces as `HTTPError` with code 302. That code is under 500, so the client raises a `ClientError` and does not retry. `map_names` records no reply, so `main` takes the replies==0 path: it logs the attempt, removes the marker and exits 4. The one shot is not used, which is the outcome L-3 asked for.

## Evidence

- Full suite from the product folder: `python3 -I -m unittest discover -s tests -t .` ran 187 tests in 1.2s, all OK.
- Mutation testing: I made 11 mutations, and the suite failed on every one of them. A no-op control mutation still passed (OK).

| Mutation | Result |
|---|---|
| client never adds to `committed_usd` (retries not counted) | 1 failure |
| default opener back to `urllib.request.urlopen` (follows redirects) | 1 failure |
| localhost exception allows any host | 1 failure |
| scheme check removed | 3 failures |
| preflight ignores retries (`* attempts` changed to `* 1`) | 2 failures |
| name-length check removed | 1 failure |
| name-count check removed | 1 failure |
| request-size check removed | 1 failure |
| price `<= 0` check removed | 2 failures |
| `total > max_usd` check removed | 1 failure |
| `preflight` call removed from `main` | 4 failures |

- Worst case with the limits at their maximum (500 names of 120 characters, 3 batches, 3 attempts each): `preflight` gives **$0.3128**.
- Cost math matches how gpt-5-mini bills tokens:
  - Chat Completions sends `max_completion_tokens` and the Responses API sends `max_output_tokens`, both set to 16,000. On both APIs that cap includes reasoning tokens, and reasoning tokens are billed as output at $2.00/M. So 16,000 tokens times $2.00/M, or $0.032 per attempt, is a true upper bound on output.
  - Each attempt is charged against the cap before it is sent. That covers timeouts and 5xx errors that may still be billed.
  - The preflight and the client use the same price (`DEFAULT_PRICE`), the same batch size (200) and the same `SYSTEM_PROMPT` and `build_user_message`. Their estimates therefore agree, and the client-side cap cannot trip partway through a run that passed preflight.

## `--expect-sha` claim (README line 17)

`score.py:156-160` compares `--expect-sha` with **`sha256_file(--gold)`**, which is the sha256 of the gold CSV. It does not compare the prompt sha. `benchmark/mapping/FROZEN.md` (commit ec262b5, branch `T-111-labels`) records `gold.csv` as `6323f7fbfad3c358223840452c08e973a0b41fa431a68d98f936a27d17c7669d`. I recomputed the sha256 of `gold.csv` on `origin/p/holiday-pay-payroll-lookback-audit/T-111-labels` and got the same value. **The README value is correct.** `ae175fa9…` is the prompt sha, which is a different thing: `run.json` records it, and `score` reports it. The README should not be changed.

## Critical issues

None.

## Suggestions (non-blocking)

1. **The cap applies to one run, not across retries of the whole run.** `committed_usd` lives only in memory. After a no-answer attempt (exit 4), each re-run can spend up to the worst case again, about $0.31. There is no limit on the number of re-runs. Fix: in `run.main`, add up `cost_usd(input_tokens, output_tokens)` from the `earlier` attempts and subtract it from `--max-usd` before calling `preflight`. Billing from 5xx or timeout attempts is usually zero or small, so this is Low.
2. **The input estimate of 3 characters per token is not a strict upper bound.** CJK text or emoji can take one or more tokens per character, and the schema and message framing add a few hundred tokens that are not counted. The effect is small, because `MAX_REQUEST_CHARS` and `MAX_NAMES` cap input at roughly $0.03 to $0.05 per attempt even in the worst case, against the $2 cap. Fix: either estimate at 1 token per character, or comment that the bound holds only within the size limits.
3. **The $2 default never binds within `MAX_NAMES`.** The largest possible worst case is $0.31, so only the size limits actually stop a run. T-120 suggested a default of $0.25. The brief set $2 (Q-16), so this is fine, but a default of about $0.50 would make the cap a real second line of defence.
4. **New test classes come after `unittest.main()`.** In `tests/test_mapper.py:651`, `SpendCapTests` and `TransportSecurityTests` are defined after `if __name__ == "__main__": unittest.main()`. `discover` finds them, but `python3 tests/test_mapper.py` skips them without warning. Fix: move the `__main__` block to the end of the file.
5. **Duplicated finiteness check.** The `--max-usd` check in `run.py` repeats the logic in `set_spend_cap`. A small `_positive_finite()` helper shared by both would remove the duplication.
