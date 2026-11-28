# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.

- Run 0297 (T-213): tender eval scorer now marks a word or page limit the AI invents (where the pack sets none) as wrong in A2, and reports whether it found the submission deadline (not a pass bar). Reviewer PASS after one fix round; suite 1250 pass, 1 skip. This was the last decision before the answer keys freeze (T-206).

- **Tender drafter (T-206 done, run 634d):** the answer keys and the 9 held-out packs are now frozen. A hash file plus a test catches any later edit, so the eval cannot be quietly adjusted after the model runs. New free diagnostic: hand labels for the 3 demo packs show the search finds the right evidence only 68% of the time in its top 8, and 52% in the top 5 the drafter actually sees (target 80%). Next fix, costing nothing: smarter search queries (T-214). No questions.
