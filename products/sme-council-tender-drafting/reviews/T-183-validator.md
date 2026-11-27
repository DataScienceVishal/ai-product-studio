# T-183 validator review: demo SPEC fit for the architect

- Reviewer: validator, 2026-11-27
- Under review: `products/sme-council-tender-drafting/SPEC.md` (strategist draft, then the validator fixes listed below)
- Context: Vishal chose Q-18 C, to build the best parked idea as a portfolio demo while knowing it scores below 70. This review is **not** a G1 re-score. The idea stays at 60 (REVISE, G0).

## Verdict: PASS (after the validator's fixes below)

The spec was close. It had one real defect: A6 contradicted itself. It also had one feasibility gap: the evaluation's token cost was not accounted for under the $6.10 a month AI cap. A few smaller wording and data-hygiene items needed fixing too. All of them were small and clear, so I applied them to SPEC.md myself (listed below). With those changes the spec is fit to hand to the architect (T-184).

## Evidence by check

### 1. Acceptance bars: measurable, pre-registered, achievable in two weeks. PASS after fixes F1 to F3
- Every bar (A1 to A9) has a number and a method. Hand-made keys built before any model run, held-out packs and a human sample are all good practice, in line with the T-66 and T-80 lessons in `playbooks/pipeline.md`.
- **Defect (F1).** The old A6 set "**0** unsupported claims in exported drafts" and, in the same cell, allowed the checker to miss up to 5% (2 of 40) of seeded false claims. A missed claim is never flagged, so the export gate can't block it. The bar couldn't hold as written. I split it into three parts:
  - **A6a:** the checker catches at least 38 of 40 seeded false claims, injected into fixed fixture drafts so the checker is tested on its own.
  - **A6b:** the export gate blocks 100% of flagged drafts (a deterministic test).
  - **A6c:** a human finds 0 unsupported claims in the exported drafts that were sampled, with the A6a miss rate stated next to it.
- **Defect (F2).** The bars were "proposed by the strategist", with no freeze point. I added a pre-registration rule:
  - the bars, keys, trap set and run configuration are committed before any scored run, and `EVAL.md` records that commit hash;
  - any change after that is a dated amendment;
  - tuning uses the 3 demo packs only;
  - A5 uses a random sample with a fixed seed.
- **Feasibility gap (F3).** FakeAI can't produce the numbers, so the eval needs live tokens. My rough estimate (method in SPEC section 3) is about 150k tokens per 40-page pack end to end, so 9 packs come to about 1.35M tokens. That is about 14 days of the 98,000-a-day cap and about $2.70 of the $6.10 a month, before any tuning (starter README lines 109-110 and 210-211 for the cap and price). That doesn't fit two weeks alongside development. Fixes:
  - extraction bars (A1 to A3) run on all 9 held-out packs;
  - drafting and claim bars (A4 to A8) run on the trap set plus 3 held-out packs chosen by a fixed rule;
  - the run configuration is fixed first (model, reasoning effort, output cap, truncation rule), as the pipeline's T-66 lessons require;
  - long packs are chunked;
  - the architect must show that everything fits, or else cut to 2 packs or ask first for a one-off eval budget.
- Once cut, the bars are achievable in two weeks of runs. A1 and A2 at 90% are plausible on digital packs; image-only PDFs are now excluded (F7).

### 2. Demo data plan: public OGL plus made-up data, no personal data, no scraping, no accounts or spend. PASS after fixes F4 to F6
- Packs come from Contracts Finder and Find a Tender, which publish under the OGL through official APIs. This was confirmed at G1 (idea file, Validator notes). The plan logs per-attachment terms and drops any pack whose terms are unclear, and it bans portal logins and scraping. Good.
- **F4.** The firm name "Northgate Facilities Ltd". A Companies House search found no exact match, but there are several live "Northgate" companies (for example Northgate Company Services Limited 05121327 and Northgate Properties Ltd 07495042), and the Northgate brand is widely known among council suppliers. A fictional firm shouldn't be confusable with a real one. I renamed it to a placeholder marked "(fictional)" and required a logged Companies House check before use.
- **F5.** Clients are now three **fictional** councils (previously "three councils", which could have meant real ones in invented case studies), and staff in case studies are roles, not names.
- **F6.** The personal-data screen now covers personal emails and direct phone numbers as well as names and signatures. If attachment download needs an API key or account, the builder stops and asks first.
- There is no spend beyond the existing approved AI cap, and any increase is ask-first.

### 3. Honesty about the 60 and about competitor parity. PASS after fixes F8 and F9
- Section 0 states plainly that the idea scored 60, was never validated, no buyer has been spoken to, CleanTender sells the same job at £99, and Competition is 1. That is accurate against the idea file's score table and the T-57 re-score.
- **Spot-check, CleanTender homepage (https://cleantender.co.uk/, fetched 2026-11-27).** The page shows:
  - Pro at £99 a month or £990 a year ex VAT, a free plan, and a 7-day Pro trial after adding a card;
  - soft FM sectors: cleaning, security, grounds, waste and hygiene, catering;
  - a "one-click claim check on every answer";
  - a compliance vault with expiry reminders;
  - a 0 to 100 fit score and a Bid, Borderline or No-bid verdict;
  - Word download after editing;
  - nothing on whether the claim check blocks export.

  So every row in the SPEC comparison table matches, and the hedge on differentiator 1 ("not confirmed ... a design choice, not a proven edge") is correct.
- **F8.** The price row said "indicative £79 to £99", but section 8's hypothesis is £59, £99 and £249. I changed it to "untested hypothesis £59 to £249 a month".
- **F9.** "Equal on extraction, drafting and claim check" is a paper comparison, because nobody has used CleanTender (a trial needs a card, so it is ask-first). I added "on paper".

### 4. Scope cut hard enough for two weeks on `products/_starter`. PASS after fixes F7 and F10
- The Must list is the seven-step core flow plus the eval and one end-to-end test, on the starter's tenancy, auth, AI adapter and FakeAI. Prices and portals are excluded. That is right for a demo.
- **F7.** The cuts:
  - embeddings move to Should (Postgres full-text only), saving AI budget and setup;
  - OCR of image-only PDFs is now a Won't, and such packs are dropped at selection;
  - true Word footnotes move to Should (python-docx has no footnote API), so the Must is inline `[E-n]` markers plus the evidence appendix;
  - Should items start only after every Must is done and A6 has passed.
- **F10.** Added a target stage: a private G3-equivalent demo, not G4. The idea stays at G0 (REVISE 60), and moving beyond the demo needs a new G1 score of 70 or more. This keeps the WIP and pipeline rules honest. Note for the Lead: the demo occupies one of the two G3 slots while it is built.
- The fictional evidence library is now 20 to 40 documents (was about 40), so writing it doesn't swallow the fortnight.

### 5. Selling lock and ask-first list. PASS after fix F8 wording
- No price appears in the app or the demo, and nothing is loaded into `app/billing.py`. Pricing is labelled a hypothesis.
- Pilot metrics apply only after `unlock selling`. There is no outreach, no live payments and no portal accounts.
- Model spend beyond the cap and a CleanTender trial are both ask-first.
- **Wording fix:** "Measured, published bars" now reads "documented bars ... shown in the private demo (nothing is published)", so it doesn't imply public publishing.

### 6. Procurement Act invented-claims risk. PASS after fix F11
- Section 10 cites Sch. 7 para 13 correctly (an "incomplete, inaccurate or misleading" example of improper behaviour, a discretionary exclusion ground). The controls are retrieval-only drafting, gap markers, a separate claim check, an export block, named sign-off and an evidence appendix. The spec states the residual risk without claiming "zero risk", and the controls are now measured by A6a to A6c.
- **F11.** "The product must say plainly that the firm remains responsible" was a risk note, not a build item. It is now in the core flow and the Must list: a statement on the sign-off screen and in the export footer. Step 6 is renamed "Coverage check" and described as a checklist, not a statement that a bid is "compliant", in line with the Won't list.
- PPN 017's disclosure is supported by the export header, and the spec correctly says PPN 017 formally covers central government only.

## Fixes applied to SPEC.md (validator, T-183)
| # | Section | Change |
|---|---|---|
| F1 | 6 | A6 split into A6a (38 of 40 seeded false claims caught, on fixture drafts), A6b (100% of flagged drafts blocked), A6c (0 unsupported claims found by a human in exports, miss rate stated); headline text updated |
| F2 | 6 | Pre-registration rule: bars, keys, trap set and run configuration committed before scored runs, commit hash in EVAL.md, dated amendments only, tuning on demo packs only; A5 random sample with a fixed seed |
| F3 | 3, 6 | Eval token estimate and method; A1 to A3 on 9 packs, A4 to A8 on the trap set plus 3 held-out packs (fixed rule); run configuration fixed first; chunking; architect must show the fit or cut, or ask first |
| F4 | 5 | Fictional firm renamed from "Northgate" to a placeholder marked (fictional); Companies House check logged in SOURCES.md |
| F5 | 5 | Fictional councils as clients; staff as roles, not names |
| F6 | 5 | Personal-data screen adds emails and phone numbers; stop and ask first if downloads need a key or account |
| F7 | 2, 3, 4 | Embeddings and Word footnotes moved to Should; OCR is a Won't; Shoulds only after Musts and A6 pass; evidence library is 20 to 40 documents |
| F8 | 7 | Price row corrected to £59 to £249 hypothesis; "published" changed to "documented, private demo" |
| F9 | 7 | "Equal" qualified as "on paper" (CleanTender untested; trial is ask-first) |
| F10 | 0 | Target stage: private G3-equivalent demo; the idea stays at G0 60 |
| F11 | 2, 4, 10 | Firm-responsibility statement on sign-off and export; "Compliance view" renamed "Coverage check" |

## Notes for the architect (T-184), not blocking
- Measure tokens per pack on one demo pack first and replace the F3 estimate in `state/BUDGET.md`.
- Check that the starter's per-call reservation and trial share fit chunked extraction calls (starter README, "Sizing the daily AI cap").
- Consider reusing the T-56 quote-trace scorer (branch `p/pepr-packaging-data-pipeline/T-56`) for A4 citation resolution.

Sources checked in this review: https://cleantender.co.uk/ (fetched 2026-11-27); Companies House search results for "Northgate Facilities" (https://find-and-update.company-information.service.gov.uk/company/05121327/filing-history, https://find-and-update.company-information.service.gov.uk/company/07495042, accessed 2026-11-27); `products/_starter/README.md`.
