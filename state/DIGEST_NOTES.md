# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.
- T-154: holiday-pay audit no longer takes or shows the reason a week is excluded (no "statutory" sick or maternity label), and worker IDs are masked in error messages. Reviewer passed it after one round of small fixes, the calculations are unchanged, and 336 tests pass. (run fda7)
- T-157: QA bug hunt on the holiday-pay audit found 6 small input/message bugs (worst: a file missing its header row could print a worker ID in an error message). All fixed and reviewed, calculations unchanged, 347 tests pass. (run 7fa4)

- run 0abb: Vishal's 1A/2A applied. Holiday-pay AI sorting test ran once ($0.006): 92.5% correct vs 95% needed, so the idea is killed (second failure; validator confirmed, no rescue). The demo build it would have started is cancelled; no idea now qualifies for the conditional build. Engine kept for reuse. Needs a direction decision next digest (no idea within 10 points of the bar).
- run f424 (T-159): checked whether any parked idea (58+) could be built under the conditional rules: none can reach 70, because rivals already sell the same job. Q-18 now recommends one 30-minute demo chat with your friend's business (needs your yes); without an answer the studio keeps desk scouting on your edges.
- run f424 (T-160): another desk scouting round on your edges tested 14 ideas and none survived; each already has a cheap competitor or a free feature in Xero/QuickBooks/FreeAgent. This is more evidence for Q-18 A.
- T-161: security check of the starter's newest code found one medium issue (the switch that turns AI off after a pricey model is detected resets when the app restarts) and two small ones. Nothing is live, so nothing is at risk; fixes queued as T-163. (run 6fea)
- T-162: QA bug hunt on the starter's AI cost guard found 4 bugs (worst: a pricier model variant like gpt-5-mini-pro could be priced as the cheap one). All fixed, reviewed and merged; 712 tests pass. (run 6fea)
