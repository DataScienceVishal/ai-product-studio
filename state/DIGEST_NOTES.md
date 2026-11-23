# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.

- [studio] Kit moved to the repo root so scheduled runs can find CLAUDE.md and scripts/.
- [studio] T-1 blocked: Telegram and Azure OpenAI env vars not set yet.
- [ideas] T-3 done: 15 G0 ideas scouted (5 from your seed directions, 5 UK SMB verticals, 5 pricing/data ideas in India and Indonesia). Validation and ranking under way (T-4).
- [studio] T-2 built: a daily Azure spend report writes to BUDGET.md (waiting for review; needs AZURE_CREDENTIALS to run).
- [_starter] T-6 built: sign-in, tenancy, test-mode billing, AI with usage caps, React app, CI. 55 tests and the browser end-to-end test pass. Waiting for reviewer and security.
- [_starter] CI is green on GitHub (_starter-ci: 5 passing runs on the branch).
- [ideas] T-4 done: no idea reached the 70-point bar. Best: restaurant margin copilot 66, MTD prep 65, wedding venue agent 63. Two India/Indonesia pricing ideas were killed (no lawful data). Evidence passes on the top two and a sharper scouting round are next.
- [ideas] MTD prep: Dext Solo and Sage's MTD agent already cover most of it. A narrower wedge survives (scans, photos and spreadsheets in, reviewed quarter totals out to any filing tool). Parked until an extraction benchmark can run, which needs your Azure OpenAI setup (T-1).
- [_starter] First review CHANGES (8 blocking) and security FAIL (5 of 8 sections): all blocking and High/Medium items fixed with regression tests (113 backend tests, e2e passes, CI green including image build and dependency audits). Re-review and security re-test running.
- [studio] T-2 spend report passed re-review. It closes after one real run with your Azure secret on main (SETUP.md step 3 explains the one manual run).
- [ideas] Round 2: pEPR packaging data scored 68, the best so far (merged with the Plastic Packaging Tax idea). Its next step is a spec-sheet extraction benchmark, which also needs Azure OpenAI. CBAM, NHS carbon plans and ESOS parked (56-58).
- [_starter] Full CI passed on GitHub, including the browser end-to-end test and the production image build.
- [ideas] pEPR (68) parked: Repackd, a UK self-serve tool, already sells spec-sheet extraction, recyclability ratings and fee simulation from £299/month. Q-4 asks which customers round 3 should scout among; your friend's business's own customers would give the studio a channel incumbents can't copy.
- [_starter] Security gate PASSED (8 of 8 sections) after three rounds of fixes. The code review's fourth pass is running; when it passes, the starter is done and products can be built from it.
- [_starter] T-6 DONE: the product starter passed both gates (code review and security). Every future product starts from it. It reaches main when you merge the branch (Q-1).
- [studio] `main` now has all of the studio's work (fast-forwarded to af446d6), and from now on everything is committed and pushed to `main`, as you asked. For the scheduled runs to push there too, switch on "Allow unrestricted branch pushes" for them (SETUP.md step 6).
- [ideas] Round 3 (T-22): 5 UK finance, tax and data ideas, all REVISE (average 53). Best: a holiday-pay look-back audit for payroll bureaux at 63, the first idea whose gap is confirmed on the incumbents' own pages. A kill test and evidence pass (T-23) start now; it reaches 70 only if every remaining piece lands. 30 ideas scored, none at 70 yet.
- [_starter] T-21 done: the last starter follow-ups passed review (147 tests, CI green).
- [ideas] Restaurant margin copilot (66) parked: Jelly (£129 per site a month) and MarketMan already sell invoice reading, recipe costing and margin alerts. The top three ideas are now all parked; holiday-pay (63) is the live candidate (T-23 running).
- [ideas] Holiday-pay (63) survives its kill test (no payroll tool documents a look-back), but is parked until the government publishes its consultation response and the Fair Work Agency's calculator scope is known. With all top ideas parked, the studio's next lever is Q-4: your friend's sector.
- [_starter] T-7 done: the Azure deploy design passed re-review, and its templates now compile in CI with a cost guard. Nothing is created in Azure until you answer Q-5 and set STUDIO_AZURE_APPROVED=yes. Open question from the architect, not urgent: does your GitHub account have Pro? If so, the deploy secrets can move into a main-only environment.
- [ideas] Round 4 (incumbent refusals): 9 of 11 candidates already had an add-on; the 2 scored were killed (margin-scheme VAT, 45: VAT Margin sells it) and parked (charity fund coding, 52). 32 ideas scored, none at 70. Lesson: search for the job itself, not just add-ons to one tool.
- [_starter] T-16 done: one image now serves the app and the API from one address, which is what a browser demo on Azure needs (review passed, CI green).
