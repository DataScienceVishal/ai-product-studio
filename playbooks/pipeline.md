# Pipeline, gates and scoring

## Stages and gates

| Stage | Meaning | Gate to move on (checker) |
|---|---|---|
| G0 Spotted | a problem and who has it | scout's idea file has 3+ pain signals and 2+ price points; validator scores it |
| G1 Validated | evidence of pain and willingness to pay | validator: 70+ points and no red flag |
| G2 Specified | spec, architecture, cost | strategist SPEC.md and architect ARCHITECTURE.md; reviewer confirms feasibility; cost fits the budget |
| G3 MVP built | the core flow works end to end on Azure | qa and reviewer PASS on the core flow |
| G4 Sellable | every line of `definition-of-done.md` | security, qa and reviewer PASS on every line |
| G5 Handover-ready | packaged for the business owner | teacher BRIEF.md, gtm kit, handover pack, then Vishal's yes |

Record each gate decision in the idea or product file's Gate log and in `state/DECISIONS.md`.

## Scoring rubric (100 points)

| Criterion | Points | What earns them |
|---|---|---|
| Pain | 20 | the problem is costly and frequent, shown by complaints, job ads for the manual task, reviews of current tools |
| Willingness to pay | 20 | businesses already pay for this (competitor prices, staff hours, agency fees) |
| AI advantage | 15 | AI is essential and hard to copy in a week (workflow depth, domain data, evaluation quality, local language) |
| Reachability | 10 | buyers can be found and reached by a small business (directories, associations, marketplaces, local networks) |
| Build feasibility | 15 | the studio can reach G4 in about four weeks of runs, on the default stack, within the Azure budget |
| Competition | 10 | scored on the studio's wedge, not on whether a rival exists: a nameable, evidenced advantage over the incumbent the buyer would otherwise pay (cheaper for a segment it prices out, better fit for a segment it ignores, UK rules it doesn't handle, a measured quality gap). No evidenced wedge: 0-3. Rival exists but a wedge is evidenced: 5-10 by strength of evidence (changed 2026-11-24, Q-10 A) |
| Risk | 10 | 10 means low regulatory and ethical risk; subtract for personal data at scale, hiring or assessment decisions, children's data, health-adjacent data, voice or biometric data |

**Red flags (automatic KILL):** an off-limits area; depends on paid services that can't be approved; depends on scraping sites that forbid it; the core value can't be shown without real customer data the studio can't get.

## Evidence standards

- Every claim cites a source URL and access date. No invented numbers. Label estimates and show the method.
- Minimum for G1: 3 independent pain signals, 2 competitor prices or a clear substitute cost, 1 realistic way to reach buyers.
- Write down what would prove the idea wrong.

## Proof-test route (added 2026-11-24, T-55)

An idea scoring 63 to 69 with no red flag may run one time-boxed benchmark before its G1 attempt counts. Write the numeric kill test first (metric, dataset, pass mark) in the idea file and commit it before running anything. Use public or synthetic data only. If it passes, the validator re-scores with the result as evidence; if it fails, that counts as a failed gate attempt. The 70 bar does not change.

Lessons from T-56 (added 2026-11-25, T-66), required in every kill test:
- **Score a pass first.** Write the score a pass would give. If a pass can't reach 70 alone (for example Competition stays low), collect the wedge evidence first and don't spend on the benchmark yet.
- **Fix the run configuration too:** model, reasoning effort, output-token cap and how a truncated or incomplete answer is handled (one retry at a larger cap, or chunking). Be generous with the cap on cheap models. Log output tokens per item during tuning.
- **Start extraction tests on the cheap model.** Move up only if accuracy needs it.
- **Keep every amendment in the idea file**, dated, not only on a branch.
- **Reuse the T-56 kit** (generator, quote-trace scorer, ledger spend guard on branch `p/pepr-packaging-data-pipeline/T-56`) for any "documents into fields" test.

## Kill rules

- An idea that fails a gate twice is killed. Write the reason, the lessons and what would revive it in its file, then move the file to `state/ideas/killed/`.
- A G3 product that goes two weeks of runs without progress on the core flow gets a review: cut scope or kill.

## WIP limits

At most 2 products in G3 and 1 in G4. Everything else waits in G1 or G2, ranked in `state/ideas/RANKING.md` by score, then by build feasibility.
