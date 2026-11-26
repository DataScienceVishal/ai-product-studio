# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.
- Round 20 (T-132, second-checker review jobs in finance/compliance): 0 of 5 survived; AI first-pass review is already sold (Adclear, Sedric, Xero Syntax free, IRIS AI, free R&D claim checkers). One focused AML file-review check (T-133) follows.
- T-133 AML file review for small accountancy practices: DROP (no public price; HMRC fines are mostly for late registration, not file quality; FCA takeover date unconfirmed). Desk rounds 18-20 all found nothing. Buyer notes from the friend remain the only input that is likely to change that (BUYER-INTERVIEW.md).
- T-134: holiday-pay test clean-up merged (291 tests, no resource warnings); report now lists workers with a non-1-April leave year. No change to the idea's status (parked at 64, waits for Q-16).
- T-135: blind differential test of the holiday-pay engine (330 random cases in the suite) found one real bug: fixed-pay workers' overtime-only weeks were left out of the average, so holiday pay due came out too low. Fixed, reviewed, merged (295 tests green). Idea still parked at 64, waits for Q-16.
- T-136: holiday-pay follow-ups merged (306 tests green). Rows that can't be checked no longer show a fake underpayment. A new blind test of the rolled-up path found nothing wrong. Review found a bug that was already there: with no contract rate given, the engine guesses an old rate after a pay rise, so it can miss underpayments. That fix is T-137. Idea still parked at 64.

- Run 9953 (T-137): holiday-pay audit no longer misses underpayments after a recent pay rise when the payroll export has no contract rate. It now uses the latest basic before the leave and always lists any week where the rate had to be guessed. Long-sickness weeks no longer give a false overpayment. Reviewer PASS after two rounds of fixes; 314 tests green.
- Run 9953 (T-138, T-139): follow-ups to the same fix. A week with some holiday in it no longer triggers a false "rate guessed" listing, and after a long unpaid gap the rate comes from the last full working week. Both passed review; 317 tests green.

- 2026-11-26T13:25Z T-140 done: last surviving mutant in the holiday-pay rate fallback is now killed by a test (318 tests green).
