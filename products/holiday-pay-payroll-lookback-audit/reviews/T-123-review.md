# Review: T-123, cumulative USD cap across no-answer re-runs

Branch `p/holiday-pay-payroll-lookback-audit/T-123` at a35fa68, compared with origin/main. The change touches `mapper/run.py` (+42/-5) and `tests/test_mapper.py` (+51).
Reviewed in a scratch worktree. Tests: `python3 -I -m unittest discover -s tests -t .` gives **192 OK**.

## Verdict: CHANGES (tests only; the product code is correct)

## Summary

The code does what the T-122 Low finding asked for:
- `preflight` adds the recorded `worst_case_usd` of earlier `attempts.jsonl` entries to this run's worst case. It refuses with exit 2 if the total is over `--max-usd`.
- The refusal comes before `set_spend_cap`, before `os.makedirs`, before the `run.started` marker, before any call and before any write to `attempts.jsonl`.
- A legacy entry with no `worst_case_usd` counts at this run's size.
- `read_attempts` now rejects lines that are not objects (exit 3).
- `run.json` records `earlier_attempts_worst_case_usd` and `cumulative_worst_case_usd`.

The one-shot rule is unchanged: `live_run_exists`, the `run.started` marker and the check that a re-run uses the same `config_sha256` are all untouched. The change does not touch `mapper/prompt.py`, KILL-TEST.md or the prompt sha.

I called `earlier_worst_case` directly to check that it fails closed. Each of these raises ValueError, so the run is refused:

| Input | Result |
|---|---|
| -1, NaN (json.loads accepts the `NaN` literal), inf, True, "0", [1] | invalid `worst_case_usd` |
| a non-dict entry, a None entry | not an object |

A `{}` entry counts at this run's size, and an empty list sums to 0.0. A missing file gives `[]`.

## Critical issues

1. **`tests/test_mapper.py`, `test_corrupt_or_malformed_attempts_fail_closed` (about line 225): the new fail-closed checks are never exercised.**
   - The cases written as `{"worst_case_usd": ...}` have no `config_sha256`. Preflight's checks pass them, and then the later config-mismatch check refuses them with exit 3. The test accepts `(2, 3)`, so it passes either way.
   - Mutation results (each mutant run against the full suite, and the suite stayed green):
     - deleting the whole range/type check (`or not (0 <= value < inf)`): 192 OK
     - dropping the `0 <=` part: 192 OK
     - dropping the `< inf` part: 192 OK
     - removing the non-dict check in `read_attempts`: 192 OK
     - removing the non-dict check in `earlier_worst_case`: 192 OK
   - Without these checks, a negative or NaN entry would quietly lower or disable the cumulative cap (`before + total > max_usd` is False for NaN). That is the exact path this task is meant to protect, and today nothing catches a regression on it.
   - Fix:
     - Write each malformed-value entry with the real `config_sha256`, either from a first failing run's entry or from `run.config_sha256(...)`.
     - Assert exit **2** exactly for value errors and exit 3 for JSON and non-object lines, plus `c.calls == 0` and that `run.started` is absent.
     - Add a `NaN` case (`'{"worst_case_usd": NaN, ...}'`).
     - Re-run the mutations above and confirm that each one now fails.

## Suggestions

- **The runtime spend cap is still per run** (`run.py` around line 190): `client.set_spend_cap(args.max_usd, ...)`. Preflight already bounds this run to `max_usd - before`, so this is defence in depth only. Passing `args.max_usd - before_usd` would make the client-side backstop cumulative as well.
- **Boundary test** (`test_cumulative_cap_boundary_allows_exact_fit_and_records_totals`): the `+1e-6` slack means changing `>` to `>=` survives (192 OK). If the intent is "exactly equal is allowed", put the cap exactly at the rounded `2*w` sum. Otherwise drop the word "exactly" from the comment.
- **`main` calls `earlier_worst_case` twice** (once inside preflight, once for `before_usd`). It is cheap and correct. Returning `before` from preflight would remove the duplication and the "validated by preflight" coupling.
- **The two exit codes are inconsistent but harmless**: a non-object line exits 3 ("unreadable") from `read_attempts`, while a bad value exits 2 from preflight. A one-line comment would help whoever writes the tests.

## Mutations that the tests do catch

- Counting legacy entries as 0: 1 failure.
- Leaving out the earlier total in the cap check: 3 failures.
- Not recording `worst_case_usd`: 1 error.

---

## Re-review at e504540

Tests: `python3 -I -m unittest discover -s tests -t .` gives **Ran 199, OK**. Since a35fa68, the only product-code change is one line in `run.py`, which sets the client spend cap to `args.max_usd - before_usd`. The test changes resolve critical issue 1.

### Mutation re-run (each mutant run against the full suite)

| Mutant | Result |
|---|---|
| Delete the whole range/type check | caught (2 failures) |
| Drop `0 <=` | caught (1 failure) |
| Remove the non-dict check in `read_attempts` | caught (1 failure) |
| Client cap set back to `args.max_usd` | caught (1 failure) |
| Drop `< inf` | survives. This is an equivalent mutant: inf makes `before + total` inf, which is over the cap, so the run is still refused with exit 2 before any call. Still fails closed. |
| Remove the non-dict check in `earlier_worst_case` | survives. `read_attempts` now rejects non-object lines first, so `main` can no longer reach this check. |
| `>` changed to `>=` at the boundary | survives. Suggestion only, unchanged from the first review. |

### The questions you asked

- **Exit 3 from `read_attempts` for corrupt JSON and non-object lines.** This is acceptable fail-closed behaviour. The run is refused before preflight, before any call and before any write. Exit 3 ("refused: attempts.jsonl is unreadable") matches the other refusals about the state of the out dir.
- **Is the non-object check in `earlier_worst_case` dead code?** In `main`, yes. `preflight` is a function other code can call and it takes `earlier` as a parameter, so the check stays useful as a guard for those callers. Keep it. An optional direct unit test would be `run.earlier_worst_case([[1]], 1.0)` raising ValueError.

### Client cap

The remaining budget is `max_usd - before`. Preflight guarantees `before + total <= max_usd` with `total > 0`, so this budget is always above zero. One edge: the recorded `worst_case_usd` is rounded to 6 decimal places. When the cap fits almost exactly, within about 5e-7, the client may refuse the last request. That failure is safe (no request is sent) and is not worth changing.

### Verdict: PASS
