# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.

- Run 42f7 (T-216 slice 4, done): added a free, label-free reranking step (pseudo-relevance feedback) to tender evidence search. Recall at 8 went from 0.745 to 0.764 and the right top passage is now found for every demo question (primary hit 1.000, was 0.964). The gain is small, inside the noise. Reviewer PASS; 1330 tests pass. Retrieval tuning is closed for now. Next: T-219, the L1 freeze and the live eval inside the $6 you approved (Q-19).
