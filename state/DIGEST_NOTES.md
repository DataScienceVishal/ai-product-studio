# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.
- Tender demo: drafting (S5, T-189) merged. Each checklist question now gets a draft answer from the firm's evidence with [E-n] citations; with no matching evidence it writes a 'needs firm input' gap without calling the model; citations outside the found evidence are flagged; over-long answers are shortened then trimmed; edits make new versions. Reviewer PASS after one round, full suite 967 green. Next: S6 claim check and export gate (T-190).
- Tender demo: S4 review leftovers (T-198) merged: stuck packs now reset after a worker crash, duplicate question numbers prevented by a database rule, page numbers clamped. Two small should-fixes queued as T-200.
- run d958: Vishal's "1A" applied: $6 one-off cap approved for the tender demo's live test (nothing spent yet; the test harness still needs fixes first).
- run d958: Tender demo: fact-checker and export lock merged. Invented clients or figures can't pass as "backed by evidence"; reviewer tried to sneak them through and the fixes held (1025 tests green).
- run d958: Tender test harness built but reviewer sent it back (7 fixes, mainly safe resume and spend tracking); next run picks it up.
- run d958: Finding: a free-trial day only covers a 3-question tender, so the demo runs on a demo account; trial limits revisit before any public trial.
- run 5bb5: Tender test harness fixed and merged (reviewer PASS): resumes safely from a fresh clone without paying twice, spend is written to disk before every call so a cut-off run can't overspend the $6 cap, and the scorers now count words and claims exactly as the app does. 1097 tests green. Still no live spend; wiring the fact-checker into the harness is next (T-202).
