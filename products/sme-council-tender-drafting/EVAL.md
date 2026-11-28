# EVAL: SME council tender drafting (template, T-193)

Status: TEMPLATE. No scored run has happened. Fill the fields marked `TBD` at the configuration freeze (L1), commit, and
record that commit hash below. After that, any change is a dated amendment, never a silent edit.

## Run configuration (pre-registered; SPEC section 6, DESIGN 8.1)

| Item | Value |
|---|---|
| Pre-registration commit (keys, trap set, fixture drafts, this file) | TBD |
| Model and version | gpt-5-mini (2025-08-07), Azure deployment named in `AZURE_OPENAI_DEPLOYMENT_MINI`; reported model must start `gpt-5-mini` or the run stops |
| API | Responses, strict `json_schema` |
| Effort and output cap per task | extract low / 6,000; draft low / 4,000; shorten low / 1,500; claimcheck medium / 6,000 (starting values, final after tuning: TBD) |
| Truncation rule | one retry at twice the cap (harness only), then the task fails |
| Reasoning headroom | 0 (`eval/budget.json`) |
| Prompt SHA-256 | from `python -m eval.run config` at the freeze: TBD |
| Retrieval | k=8, at most 3 passages per document, score floor TBD (`RETRIEVAL_FLOOR`, 0 until L1 tuning) |
| Chunk size and overlap | `CHUNK_PAGES` and `OVERLAP_PAGES` in `app/tender/extract.py`: TBD at freeze |
| Word-count rule | the app's own `count_words` (`app.tender.draft`), imported: `[E-n]` markers excluded, gap markers included, a token counts only if it holds a letter or digit (DESIGN 4.5) |
| A1 and A2 matching | a question matches by `ref` (and a text similarity of at least 0.5, so a reused number on a different item is not a match), else by text similarity of at least 0.8 (difflib ratio on normalised text), one-to-one greedy; word limits, page limits, marks and weights must match exactly |
| A3 | a key mandatory item must match an extracted item that is kind mandatory or pass/fail; matched but optional counts as "shown optional" and fails the bar. Refs are matched only against non-question extracted items (a question sharing a ref cannot pair up); text similarity can still match any item |
| A4 | claims are the app's own sentences (`app.tender.draft.split_sentences`: a citation after the full stop stays with its sentence, a `[NEEDS FIRM INPUT: ...]` marker stays whole). A sentence holding a gap marker and no `[E-n]` is exempt only if, with the marker(s) and any `[E-n]` stripped, no digit or letter+digit code (S1, H2), no number word (`score.NUMBER_WORDS`: zero, forty, ...), no negation (`score.NEGATIONS`: no, not, never, nil, ...; also cannot and any n't form), no claim word (`score.CLAIM_WORDS`: free, compliant, accredited, certified, approved, vetted, insured, award, winning, ...) and no hyphenated compound (incident-free, award-winning), so a sole assertion word is a claim, not a stub, no acronym (two or more capitals, e.g. ISO, RIDDOR), no hit from the app's claimcheck `fact_triggers` (codes, pound, percent, runs of capitalised words such as "Cyber Essentials") and at most 2 words that are not connectives (a fixed function-word list, `score.CONNECTIVES`: the, we, and, of, our, will, ...) are left; any of these, or a third content word, keeps it a claim, scored like the rest and failing without a citation (so "We hold [gap]" is exempt, "We have delivered 40 contracts for 12 councils and hold [gap] cover" is not). A gap sentence that also cites is always scored. A4 reports the number and share of exempt sentences next to the score (`gap_exempt`, `gap_exempt_share`) so the reader can see what was excluded. A claim passes with at least one `[E-n]` and every `[E-n]` live in the tenant and in the draft's retrieved set |
| A5 and A6c random seed | 20261127 (`eval/sample.py A5_SEED`); 100 claims from the E2 exports, all if fewer. A5 is exactly 100 cited claims (all if fewer), drawn from cited claims only. The A4 gap-exempt sentences (`sample.gap_exempt_rows`, ids `gap-...`) are never in that draw: they form a separate block on the same sheet, all of them, counted only toward A6c (a gap row a person judges to assert something is an unsupported claim) and reported as "exempt-but-asserting"; they do not enter the A5 numerator or denominator |
| A6a | a seeded claim is caught when a checker claim on the same draft is `unsupported` or `contradicted` and overlaps it on word tokens (never raw characters): the checker span covers at least 50% of the seeded span's distinct tokens AND either the seeded span is at least 30% of the checker span's tokens, or both lie in one app sentence of the draft. A tiny span or a whole-paragraph span therefore misses. At least 38 of 40; misses listed by type; the checker's false-flag rate (flagged claims overlapping no seeded claim) is reported beside it |
| Held-out drafting pack rule | the first of each sector in `demo-data/SOURCES.md` order (3 packs), named explicitly as `drafting_heldout` in `demo-data/packs/manifest.json` (exactly 3, all in `heldout`) |
| Budget | one-off hard cap $6.00, gpt-5-mini only, approved by Q-19 (answered A, 2026-11-27); sub-caps tuning $2.00, scored $2.60, recording $1.40; ledger `eval/ledger.jsonl`; app caps unchanged |
| Ledger rules | before each call a `hold` row (worst case) is appended to the ledger under a file lock after the cap check; an unsettled hold counts at worst case until its `settle` row, so a killed process cannot pass a cap; a call that may have been billed and left nothing is charged at worst case; the scored preflight needs the worst case of the unfinished scored phases free ($2.54 before E1) |
| Scored run | one run; `eval/results/<phase>.jsonl` and the ledger are committed after every phase; an infrastructure failure resumes from the first unfinished item; a live phase whose ledger has rows but whose results file is missing is refused |
| Tuning data | the 3 demo packs and the 10-question dev trap set only; never the held-out packs |

## Threat notes (known residuals, to be decided in L1 tuning)

Recorded in T-201 item 9. No code was changed for these; they are decided with real model output in L1.

1. **Sentence-initial one-word names still pass the quote check.** A claim that opens with a single capitalised name ("Tesco relies on us for ...") has no second capitalised word, so the two-capitalised-word name detector does not fire, and a short quote that is in the cited passage can support it. A checker that invents or mis-attributes a one-word client name can therefore mark it `supported`. Options for L1: treat a sentence-initial capitalised word that is not in a stop list as a name, or require the name to appear in the quote.
2. **The no-figure, no-name residual.** A claim with no number, code or capitalised name (for example "We have never lost a contract") has nothing for the pure rules to check, so its verdict is the model's. The rules only downgrade; they cannot upgrade or catch a false `supported` here. A5 (human sample of cited claims) and A6a (seeded claims) measure this residual; L1 decides whether to add a rule for absolute words (never, always, all, every) that need a quote containing them.
3. Both residuals fail toward a human reviewer: sign-off still requires the person to accept the responsibility statement, and nothing exports without it.

## Known limits

Recorded in T-207. Both are edges of the heading rule in `extract._is_heading` (the line above a quote that may carry its word limit). Cases are in `eval/extraction_known_limits.json` (no extraction case file existed, so this small data file is new; `tests/test_tender_extract.py::test_known_limit_cases_hold` reads it so it cannot drift). L1 decides whether to widen the rule using real tenders.

1. **False negative: a heading that addresses the bidder.** "How you will deliver social value (max 300 words)" or "What we need from you (max 300 words)" opens with a question word and says you/us, so `_is_heading` takes it for the previous question and no limit is found (cases KL-1a, KL-1b, KL-2). T-207 tried a bracketed-limit heading rule and removed it after three review rounds: in 11 of 21 realistic question lines it lent an earlier question's limit to the next one ("What training will your staff receive (max 200 words)"), which is worse than a missed limit. The user confirms every limit at the checklist step. Kept from T-207: the question's own stated limit always wins over a heading's (`_stated`), and earlier questions ending in a bracketed limit are regression cases (KL-4 to KL-12).
2. **False positive: an impersonal earlier question taken as a heading.** "Describe the proposed methodology in no more than 200 words" has no you/your/us, so it passes `_is_heading` and its limit is borrowed by the next, unnumbered question (case KL-3). A numbered next question is safe (the window starts at the numbered line). Left as is: telling it apart from a real heading such as "How we deliver social value (max 300 words)" needs more than a line-shape rule.
3. The wrong-limit flag (`stated` vs the model's limit) is the safety net for both: a mismatch is shown to the user.

## Results

TBD (L2). Per bar: value, bar, pass or fail, with the A6a misses by type and the model-checking-a-model caveat (SPEC section 6).

## Amendments

- 2026-11-27 (T-203, before the freeze, no scored run yet): A4 gap exemption tightened (claim words, hyphenated compounds, letter+digit codes, cannot and n't); claim words won, best, leading, trusted, experienced and `cant` added; exempt gap sentences added as a separate A6c-only block on the review sheet. A4 can only go down; A6c gains rows, so it can only get stricter; A5 is unchanged (100 cited claims, same draw).
