# T-206 retrieval labels: independent checker

File checked: `eval/keys/retrieval_labels.json` (branch `p/sme-council-tender-drafting/T-206-labels`).
Read: packs S04, S08, S12 (pack-sources), `eval/keys/README.md`, evidence files 01 to 32. Not read: `demo-data/evidence/README.md`, `eval/keys/trap_set.json`.

## Verdict: REVISE (three small edits; everything else holds)

### What I checked
1. **Completeness: OK.** S04 has 9 items (4.1, 4.2(a), 4.2(b), 4.3, 4.4(a), 4.4(b), 4.5, 4.6, 4.8). 4.7 (PASS/FAIL) is left out correctly. S08 has Q1 to Q10. PF-Q is left out correctly. Q5 (a)/(b) is one item, which is right under rule 3 because the parts have no weighting or limit of their own. S12 has 1 to 11. Every ref is as printed and none is duplicated.
2. **`why` accuracy:** two are false (required change 1). The rest match their files.
3. **Missed passages:** one clear miss (required change 2). Others are optional.
4. **Over-labelling:** nothing serious. One borderline case is listed under optional nits.
5. **Gaps: confirmed.** I grepped all 32 files for false / repeat / repair / handyman / electric / gas. Nothing covers reducing false alarms or repeated activations (S08 Q5). Nothing covers small repairs, pricing or reporting repair jobs, or gas and electrical work (S12 Q5). The only "electric" hits are E-5 (renewable tariff, no EVs).
6. **Primary choices:** sensible throughout.

## Required changes
1. **S04 4.8 and S12 11, `why` for E-28.** The label says "direct local recruitment", but E-28 says only "direct recruitment only; 33 hires in 2025/26". The word "local" is not in the file; local hiring (85% within 10 miles) is in E-14. Change it to "direct recruitment, apprenticeship starts, pay floor" (S04) and "apprenticeship starts, direct recruitment" (S12). Keep E-28 relevant.
2. **S08 Q2: add E-13 to `relevant` (not primary).** The question asks "the way you will keep key security to BS 7984-1". E-13 says: "the depot holds a duplicate set of site keys in a secure store". This answers key security directly. It is a stronger fit than E-12, which is already labelled. Suggested why: "duplicate set of site keys held in a secure store at the depot".

## Optional nits (judgement calls; Recall@8 effect small)
- S04 4.3 and S12 2: consider adding E-28 ("a 9-person relief cleaner bank and 4 relief officers"; "flexible shift swaps via a shared rota app"). It covers holiday and illness cover, but the relief bank is already in E-13, so it adds little.
- S08 Q3: consider adding E-9 ("Right-to-work checks are done on day one by the Finance and HR Manager"), which is part of vetting.
- S08 Q2: E-16 ("assets and keys logged", week -2) and E-26 (depot row: "64 call-outs, 22 min average") are defensible additions. E-26 repeats E-18 and E-24.
- S08 Q1: E-24 is borderline. It is a keyholding case study, and its link to monitoring is only "alarm response through Demo ARC Ltd", which E-18 and E-27 already cover. Removing it would be defensible.
- S08 Q6: consider making E-18 primary too. The honest answer is that the alarm receiving centre (ARC) is subcontracted ("We do not run our own control room"), so continuity of the ARC rests on the partner.
- S12 7: E-23 (enhanced-DBS team, "safeguarding awareness for all staff", 0 concerns) was labelled for S04 4.5 on the same child-protection point. Add it here for consistency, or drop it there.
- S12 8: E-26 (Tarn Valley parks audit 89.8%) was labelled for the S04 4.6 quality question. Add it here for consistency.
- S12 10: E-20 is one of four equally eligible non-grounds case studies (20, 21, 23, 24). Note in the derivation that the second case study was picked by size or council relevance, or label all four.
- S12 5 (gap): E-6 ("any subcontractor must show insurance and a risk assessment before starting") and E-27 ("We would tell the client before any subcontracting begins and remain responsible") only touch the gas/electrical sub-contracting route in general terms. Keeping it as a gap is right. The gap note could say these were considered.
- S08 Q5 `text` keeps only part (a). The gap note does cover (b), so this is fine; including the (b) sentence would match rule 3's "text holds both".

## Re-check (commit 3cd3a5c): PASS

I had no shell in this session, so I checked the working-tree file instead of running `git show`.
1. E-28 `why` now reads "direct recruitment, apprenticeships, pay floor" (S04 4.8) and "apprenticeship starts, direct recruitment" (S12 11). No E-28 `why` contains "local" any more; the word now appears only in question texts and E-14 `why`s, where it is correct.
2. S08 Q2 `relevant` is now [12, 13, 18, 24]. `primary` is still [18, 24]. E-13's `why` is "depot holds a duplicate set of site keys in a secure store", which matches E-13 line 8.

Both required changes are done. Leaving out the nits is acceptable, since they are judgement calls. Limit: without the diff I could not confirm that the commit touched nothing else. The rest of the file looks unchanged in what I read.
