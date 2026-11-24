# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.
- run 6224 (T-56 pEPR): realism supplement done: 12 harder synthetic sheets (weights in gm/oz, unit only in the label, gsm-only films, blends, catalogue, two-block layout, French page, encrypted PDF), reviewed PASS after one round of fixes. Scored separately; the agreed pass mark is unchanged. A UK search found 5 more public spec sheets (links only). Still waiting on Q-11 ($12 model spend) before any real run.

- 2026-11-24 run e08c: Vishal's 1A/2A applied (wedge-scored Competition in pipeline.md; $12 approved for the pEPR test). Re-score under the new rule: no parked idea reaches 70 (holiday pay 64 best wedge; restaurant 66 unchanged). pEPR tuning run started on the real model: medium effort (low is refused by the model), first sheets $0.08 and $0.32.
- 2026-11-24 run e08c: pEPR tuning done on the real model: 97.9% field accuracy on 5 sheets, all conflicts flagged, but 2 untraced values, 1 invented value, mean $0.40/sheet (mark $0.316). Test set can't start inside $12 (needs $10.50, $9.99 left): Q-12 asks to raise the cap to $20. Put Q-12 in the next digest.

## Run 591a (T-58)
- **Model price correction:** gpt-5.4-pro costs $30/$180 per million tokens, not $15/$120. Real model spend so far is about $15 of the $80 credit (up to ~$20 if two failed calls were billed), not ~$10. T-12 may have passed its $15 cap in the worst case. BUDGET.md is restated. The T-56 guard is fixed to the real price (in review).
- **Q-12 rewritten before sending:** recommend a cheap mini deployment (option A). On the pro model, the pEPR test would cost ~$18.50 and fail the cost mark.
- **Spend report bug:** the "$17,015 projected monthly" figure was a parser bug, not a real projection (real: $23.20). Fix in review.
- Spend parser fix and follow-ups merged (T-58, T-59). The starter README's pro-model cap example now uses $180/1M output (about 1,130 tokens a day for $6.10).

- run 45ef (T-15 starter): the early-customer offer (EARLY50) is now applied automatically by Stripe at checkout, not re-typed by the customer. Reviewed PASS, merged, 484 backend + 114 frontend tests green. Test mode only; nothing run against real Stripe.
