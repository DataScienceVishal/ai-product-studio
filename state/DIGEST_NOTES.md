# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.
- T-154: holiday-pay audit no longer takes or shows the reason a week is excluded (no "statutory" sick or maternity label), and worker IDs are masked in error messages. Reviewer passed it after one round of small fixes, the calculations are unchanged, and 336 tests pass. (run fda7)
- T-157: QA bug hunt on the holiday-pay audit found 6 small input/message bugs (worst: a file missing its header row could print a worker ID in an error message). All fixed and reviewed, calculations unchanged, 347 tests pass. (run 7fa4)
