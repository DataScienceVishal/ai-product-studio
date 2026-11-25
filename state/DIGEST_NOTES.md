# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.
- T-79 (run 4f19): two more parked ideas killed after a targeted re-check (order entry from email/WhatsApp, 57: Zestcode and Airdev already sell it) and the Ireland BER watch-list dropped (no pain or price evidence). 53 scored, 0 PASS. Strengthens Q-13 A (buyer chat with the friend).

- 2026-11-25 run d8d4: Vishal's 1B and 2A applied. Restaurant proof test started: rules for pass/kill written before any test (even a full pass only reaches 69 of 70 without a Jelly comparison). Invoice benchmark built, 61 tests pass; first 3 practice pages read 27 of 34 lines right at about half a penny a page. Jelly trial waits: there is no studio email to sign up with (ask Vishal for one).
- Deploy role: Vishal applies it at his next deploy (his 2A).
- T-80: DEV practice score 87% overall but 75% on phone photos, under the 80% kill line, so the real test may well kill restaurant. Test run waits on 3 small fixes from code review.

- 2026-11-25T10:50Z run 99f7: **restaurant-margin-copilot killed by its proof test (T-80).** The one pre-registered test run: clean invoices read 98.5% right, but phone photos only 72.1%, overall 82.6%, and 5 of 50 invoices had wrong numbers that still added up (silent errors). All three are past the kill lines set before the run. Cost was fine ($0.01 per page; $1.12 of the $5 cap used in total). Lesson: a cheap model reads printed invoices well; tilted or shadowed photos make it read numbers from the neighbouring row. New rank 1: holiday-pay-payroll-lookback-audit (64, parked on the government response). No idea is near 70; scouting continues.
- 2026-11-25T11:23Z run 8f52: T-82 edges-only scouting round (finance/tax deadlines 2026-2028): 0 new ideas. Every deadline checked (umbrella PAYE, FRS 102 leases, payrolled benefits, Companies House filing, IHT on pensions, CIS/R&D) already has a tool selling it. New question Q-15: the buyer chat with your friend is now the main route to a 70+ idea.
- 2026-11-25T11:40Z run 8f52: security pass on the newest starter code (billing portal, redirects): PASS, two small issues fixed and merged after review (564 backend + 155 frontend tests green).

- Run 4328 (T-84 done): the starter's "mock billing" switch in the browser is now covered by tests. It turns on only when the server says "mock" and stays off if /api/config fails, times out or returns an error. The review caught two gaps; both were fixed and then passed. Merged to main with backend 564 and frontend 166 tests green. T-85 is a one-line test follow-up.

- Run eb25 (13:21Z): T-85 merged (billing_provider must be exactly "mock"; reviewer PASS). T-86 QA bug hunt on the starter: no 500s and no cross-tenant leaks; 3 UI bugs fixed (notes past 50 unreachable, endless "Loading…" on a failed load, long text overflowing on phones), in review; 5 low items queued as T-87.
