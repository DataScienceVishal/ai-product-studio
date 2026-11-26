# Review: p/_starter/T-34-cap-note (ee29e3a)

Reviewer, 2026-11-26. Diff: `git diff main...FETCH_HEAD`, 3 files, +12 / -2. Closes S-c in `reviews/T-34b.md`.

## Summary

Docs and comments only. It adds a headroom note to the README settings table, a new paragraph in "Sizing the daily
AI cap", two comment lines in `.env.example` and one reworded comment in `infra/main.bicep`. No code, test or
config value changes. S-c asked for two things: the reservation rises from about 1.2k to 2.7k in Responses mode,
and the cap formula is unaffected because caps count settled tokens. Both are now covered, in all three files.

## Numbers checked against the code

| Claim | Source | Result |
|---|---|---|
| answer budget 1,200 | `routes/notes.py:27` `MAX_SUMMARY_TOKENS = 1200` | correct |
| headroom 1,500, Responses only | `config.py:89` `ai_reasoning_headroom = 1500`; `ai.py:282` `output_headroom = ... if api == "responses" else 0` | correct |
| 1,200 to 2,700 | `ai.py:110` `reservation_estimate` = `estimate_tokens(..., max_output_tokens + output_headroom)` | correct |
| system prompt 287 bytes | `len(SUMMARY_SYSTEM.encode())` = 287 (computed) | correct |
| wrapper 17 | `notes.py` prompt `"<note>\n" + "\n\n" + "\n</note>"` = 7 + 2 + 8 | correct |
| 1 KB note: 2,504 chat, 4,004 Responses | 287+1000+17+1200 / +2700 | correct |
| empty note: 1,504 chat, 3,004 Responses | 287+17+1200 / +2700 | correct (matches the existing README text above it) |
| 98,000 / 3,004 = 32.6; 98,000 / 1,504 = 65.2 | arithmetic | correct (32.62, 65.16) |
| "caps count settled tokens, the reservation is a hold" | `ai.py` `reserve()` writes a `pending` row with `input_tokens=estimate`; `settle()` overwrites it with actual use; stale rows are zeroed | correct |
| monthly ceiling still cap x 31 x price | settled use is at most the estimate (input bytes bound input tokens; output is at most `max_output_tokens` including the headroom, and failed calls bill `max_output_tokens` after the headroom is added, `ai.py:322`/`358`) | correct |

## Bicep

The only `main.bicep` change is to the `//` comment lines above `param aiGlobalDailyTokens`. The `@description` string
and the `param` line are byte-identical. The regexes in `test_aicost.py::test_shipped_defaults_match_and_fit_the_approved_budget`
still match: `param aiGlobalDailyTokens int = 98000`, `azureOpenAiDeployment 'gpt-5-mini'`, `AI_GLOBAL_DAILY_TOKENS=98000`,
`# AI_MONTHLY_BUDGET_USD=6.10`. I checked them with the same regexes, because pytest is not installed in this
sandbox. `infra/test-deploy-role.sh` and `infra/test-deploy-workflow.sh` passed on the branch. `test-bicep-identities.sh`
and `cost-guard.sh` need compiled JSON (no bicep CLI here), and this change cannot affect them.

## Consistency with the rest of the README

There are no contradictions. The new text matches "Calls per day", which already gives 1,504 / 3,004 and says
Bicep `auto` picks chat. It also matches the existing `AI_REASONING_HEADROOM` row ("ignored for chat completions")
and the worked example (4,004, 24 calls).

## Critical issues

None.

## Suggestions (non-blocking)

1. **`.env.example` new line 1 is garbled.** "With AI_GLOBAL_DAILY_TOKENS above this lifts the answer part..."
   reads as though the lift depends on the daily cap, or as though "this" means the cap. It doesn't: the lift comes
   only from the Responses API plus this setting. Suggested wording: "On the Responses API this lifts each
   summary's reservation from 1,200 to 2,700 output tokens (1 KB note: about 2,504 on chat, 4,004 on Responses)."
2. **"answer part" for 2,700 is loose** (README table, README paragraph, Bicep, .env.example). The 2,700 is the
   whole output budget: reasoning plus answer. The answer itself still gets 1,200, which is the purpose of the
   headroom. "output part" or "output budget" would be exact. This is a nit, and the README already calls the
   1,200 the "answer budget".
3. **"Caps count settled tokens"**: pending holds also count against the caps until `settle()` (or the 15-minute
   stale sweep) replaces them. The text gets this across through "hold" and "how many calls can be held at once",
   so this is optional. "32 at once" is a ceiling from the budget only; the 8-per-process and 2-per-tenant limits
   are lower still. That is fine as written.

VERDICT: PASS
- All numbers verified against the code: 1,200 / 1,500 / 2,700 / 287 / 17 / 2,504 / 4,004 / 1,504 / 3,004 / 32.6 / 65.2.
- The Bicep edit is comments only. The test regexes on main.bicep and .env.example still match.
- No contradiction with the rest of the README. S-c is closed.
- Optional: reword the first `.env.example` line (suggestion 1) and say "output" instead of "answer" for 2,700 (suggestion 2).
