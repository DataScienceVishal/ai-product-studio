# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.
- Run c3fc: T-98 done. The new built-page check now reads HTML properly (no false alarms from text inside attributes) and also catches javascript: links. Two reviews PASS, 670 backend tests green, merged.
- Run c3fc: T-94 done. The Billing page no longer over-promises: while billing is in test mode it says every plan uses the free-trial AI allowance (100,000 tokens a month, 30,000 a day). Reviewer PASS, 673 backend + 205 frontend tests green, merged.
