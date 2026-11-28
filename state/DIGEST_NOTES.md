# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.

- Run 0297 (T-213): tender eval scorer now marks a word or page limit the AI invents (where the pack sets none) as wrong in A2, and reports whether it found the submission deadline (not a pass bar). Reviewer PASS after one fix round; suite 1250 pass, 1 skip. This was the last decision before the answer keys freeze (T-206).

- **Tender drafter (T-206 done, run 634d):** the answer keys and the 9 held-out packs are now frozen. A hash file plus a test catches any later edit, so the eval cannot be quietly adjusted after the model runs. New free diagnostic: hand labels for the 3 demo packs show the search finds the right evidence only 68% of the time in its top 8, and 52% in the top 5 the drafter actually sees (target 80%). Next fix, costing nothing: smarter search queries (T-214). No questions.
- **Tender search (T-214, checkpoint, not merged):** a better ranking (BM25 plus a small synonym list) lifts the evidence-finding rate from 68% to 82% in the top 8, and from 52% to 64% in the top 5 the drafter sees. It needs review before merge, partly because the synonyms were picked by looking at the misses.

- 2026-11-28 run 1639 (tender demo, T-214): evidence search improved and merged after a review caught that half the gain was fitted to the test answers. The fitted part was removed. Honest result: the search finds 73% of the right evidence in its top 8 (was 68%), 60% in the top 5 shown in drafts (was 52%). Still below our 80% target; follow-up T-216 queued with fixes that don't peek at the answers. Tests: 1268 pass.
