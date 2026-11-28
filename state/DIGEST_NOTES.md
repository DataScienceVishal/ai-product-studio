# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.

- Run 42f7 (T-216 slice 4, done): added a free, label-free reranking step (pseudo-relevance feedback) to tender evidence search. Recall at 8 went from 0.745 to 0.764 and the right top passage is now found for every demo question (primary hit 1.000, was 0.964). The gain is small, inside the noise. Reviewer PASS; 1330 tests pass. Retrieval tuning is closed for now. Next: T-219, the L1 freeze and the live eval inside the $6 you approved (Q-19).
- Run 430c (T-219 slice 1): the tender demo made its first real AI calls (eval tuning only, $0.01 of the $6 approved). That one run found a real bug: the AI labels questions in its own words and the app then files them as 'other', so a real tender would show no questions. Fix queued as T-220, top of the board.

- (run 35a1) Tender drafting: the eval harness now measures the whole flow (extract, draft, claim check) in the T1/T2 calibration runs instead of extraction only. Worst case T1 $0.28, T2 $1.34, inside the $2 tuning cap. Review fixes merged (no answers served from cache, clean stops on Azure errors). 1381 tests pass. Next: T-220 (extraction kind bug, another run has it), then re-run T1 live.
