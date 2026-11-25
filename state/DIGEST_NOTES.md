# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.
- Run c3fc: T-98 done. The new built-page check now reads HTML properly (no false alarms from text inside attributes) and also catches javascript: links. Two reviews PASS, 670 backend tests green, merged.
- Run c3fc: T-94 done. The Billing page no longer over-promises: while billing is in test mode it says every plan uses the free-trial AI allowance (100,000 tokens a month, 30,000 a day). Reviewer PASS, 673 backend + 205 frontend tests green, merged.
- Run eb50: T-100 security pass on the last 53 starter commits: CHANGES with one medium finding. The AI cost guard trusts the Azure deployment's *name*, so a cheap-sounding name on an expensive model could burn the $80 credit in about 4.5 days. Needs an operator mistake; nothing is exposed today (deploys default to the fake AI). Fix in progress as T-101.
