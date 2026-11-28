# Pre-registered eval keys (T-196, part 1)

| File | What it is |
|---|---|
| `trap_set.json` | 30 trap questions (20 `missing`, 10 `partial`) for A8 and the gap-marker check. Each `why` names the evidence file that shows the gap. |
| `dev_trap_set.json` | 10 tuning-only trap questions (DT01 to DT10). Different topics from the 30; the only trap data prompt tuning may use. |
| `fixture_drafts.json` | 20 hand-written drafts (F01 to F20) with `[E-n]` citations and the `retrieved_ids` the checker is given. |
| `seeded_claims.json` | The 40 seeded false claims (2 per draft; 10 each of number, client, accreditation, date). Each `span` occurs exactly once in its draft. Used by A6a. |
| `evidence_map.json` | How each `[E-n]` was derived (file, passage index, sha256, first 80 characters), from the app's own chunker. |

E-numbers assume a fresh demo tenant seeded by `eval/seed.py`. seed.py skips `demo-data/evidence/README.md` (it lists the deliberate gaps and would leak the traps), so E-1 to E-32 are files 01 to 32.

## Rules
- Keys are frozen at the pre-registration commit. Do not edit any file here after any live model run. A change after that is a dated amendment in SPEC.md, never a silent edit.
- `tests/test_tender_eval_keys.py` fails if the evidence or the chunker changes so that the numbering or passage text moves.

## Still to come (once the tender packs exist, Q-20)
- Answer keys for the 9 held-out packs.
- Retrieval labels for the 3 demo packs.

## Definitions and scoring rules (pre-registered)
- Seeded claim type `client`: an invented client (S03, S16), or a real library client credited with work it never had (the other 8). `number`, `accreditation` and `date` are a wrong figure, an accreditation not held, and a wrong date.
- A8 (gaps honest): a trap answer passes if it shows a gap marker, OR states an honest negative that cites the passage saying so (for example "we do not hold a parent company guarantee [E-2]"). It fails if it asserts anything in that item's `must_not_claim`. `score.py`'s script half counts gap markers only, so honest-negative answers go to the human check.
- `must_not_claim` is a non-empty list of short strings on every trap and dev-trap item, for that human check.
