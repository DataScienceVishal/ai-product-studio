# T-162 review: reported-model exact match, safe model name, chat refusal

Branch `p/_starter/T-162` @ cdfeaba, diff `main...HEAD` (ai.py, aicost.py, test_ai.py, README.md, ADR 0002, QA report).
Reviewer: reviewer agent, 2026-11-26.

**Verdict: PASS**

## Evidence

- Full backend suite in the worktree (`cd backend && python -m pytest`, Postgres at
  `postgresql+psycopg://studio:studio@localhost:5432/starter_test`, venv /tmp/claude-0/venv):
  **712 passed, 1 skipped, 1 warning in 101.93s**. This matches the QA report (692 before, plus 20 new parametrised cases).
- Mutation testing, done in a scratch copy (the worktree was not edited). Ran `tests/test_ai.py` and `tests/test_aicost.py`:

| # | Mutation | Result |
|---|---|---|
| M2 | `_DATE_SUFFIX` back to `\d` (Unicode digits) | killed (Arabic-Indic date case) |
| M3 | drop the `pending`/`abandoned` mapping | killed (2 cases) |
| M4 | drop the `isprintable()` filter | killed (NUL storage, log forging) |
| M5 | drop the `[:80]` truncation | killed (500-char case) |
| M6 | drop the chat refusal branch | killed |
| M7 | log `reported[:80]` again instead of `_clean_model` | killed |
| M8 | restore the old longest-prefix lookup | killed (8 cases, including `gpt-5-mini-pro`, `gpt-5-nano-pro`) |
| M9 | store the raw reported model in `AIResult.model` | killed (4 cases) |
| M1 | drop `count=1` from the date `sub` | survived. This mutant behaves the same as the original: the pattern is anchored with `$`, so `re.sub` can only match once anyway. Not a gap in the tests. |

## Correctness

- **Real Azure names still get the right price** (checked by calling the function directly): `gpt-5-mini-2025-08-07` gives 2.0,
  `gpt-5-mini-20250807` gives 2.0, `gpt-5-nano-2025-08-07` gives 0.4, `gpt-5-2025-08-07` gives 10.0, `gpt-5-pro-2025-10-06`
  gives 120.0 and `gpt-5.4-pro` gives 180.0. A trailing newline or upper case is normalised.
- `gpt-4.1-mini`, `gpt-4.1-mini-2025-04-14` and `o4-mini` all return None. They were None on main too, because none of them
  starts with a table key followed by `-`. So nothing changes for them: they need `AI_PRICE_PER_MILLION_TOKENS`, at startup
  (`resolve_price`) and at runtime.
- **Startup deployment-name check (`resolve_price`)** is untouched and was already an exact match, so it has no regression.
  The runtime lookup now follows the same exact-match rule, which is more consistent.
- **Behaviour change, accepted and documented:** a variant name the table doesn't list now fails closed. For example, a deployment named
  `gpt-5` that reports `gpt-5-chat-2025-08-07` used to be priced at $10 and now switches AI off. With an explicit price
  set, an unknown reported model is still accepted (existing rule). This is the right direction for a cost guard.
- `_clean_model`: a non-string, a blank, `pending`/`Pending` or `abandoned` becomes `unknown`. Non-printable characters are
  removed, including NUL, CR/LF, ESC, the bidi override U+202E and lone surrogates (category Cs). The name is cut to
  80 code points, which matches Postgres `varchar(80)` because both count characters. Clean names are stored unchanged.
- The `_PENDING` filter (`model == 'pending'`) can no longer be matched by a provider string, so a settled row can't look
  like an open reservation.
- Chat refusal: a non-empty `message.refusal` with no content returns `why="refusal"` and keeps the billed token counts.
  The refusal text is never put in the user message or the log (the test asserts this). If there is content as well as a
  refusal, it still counts as an answer, which is the documented chat rule.

## Security and privacy

- No prompt, answer or refusal text is logged. The error line contains only the sanitised model name. The `ai usage` info
  log contains the sanitised model and the token counts.
- Log forging through the model name is closed, and a test covers it.
- `finish_reason` is still logged unsanitised in "ai returned no usable answer". The QA report already lists this
  (only a hostile provider could exploit it, Low). See S2.

## Docs

The README and ADR 0002 now say "exact name, one date suffix dropped", which matches the code. The `reported_model_price`
docstring is accurate. A grep finds no "longest prefix" wording left in the docs or app code.

## Blocking items

None.

## Non-blocking suggestions

1. `tests/test_ai.py:1183`: the comment `# longest prefix wins over gpt-5` is now stale. It should say that an exact match
   after dropping the date wins.
2. Run `finish_reason` through `_clean_model`, or a small sibling function, before it goes into the `extra` dict at
   `app/ai.py:400`. The same log-forging argument as B3 applies, though only a hostile provider could use it.
3. Consider adding `gpt-5-chat` (and any other variant the studio actually deploys) to `MODEL_PRICES_PER_MILLION`, so
   that legitimate variants don't trip the fail-closed path. Add each one with a sourced price in state/BUDGET.md, as a
   separate reviewed change.
4. `count=1` in `aicost.reported_model_price` is redundant because the pattern is anchored with `$`. It is harmless and
   reads as intent, so keep it or drop it.
