# T-192 e2e QA verdict: PASS (with listed gaps, none blocking the Done bar)

Branch p/sme-council-tender-drafting/T-192-e2e. Reviewer: qa. Date 2026-11-28.

## Evidence
Command (run twice, back to back, fresh DB each time): `cd products/sme-council-tender-drafting/app && NODE_PATH=/opt/node-tools/node_modules bash scripts/e2e.sh`
- Run 1: "E2E PASS: tender core flow (7 steps)" and "E2E PASS: core flow", exit 0 (logs /tmp/tmp.ME4X1NjtRV).
- Run 2: identical, exit 0 (logs /tmp/tmp.XS9ycCUUB7). No flakiness seen in 2 runs. AI is ScriptedFakeAI (tests/e2e/e2e_app.py), no model calls.

## SPEC step coverage in tender_flow.cjs
| Step | Exercised | Asserted outcome |
|---|---|---|
| 1 Upload | sign-up, create pack, upload tender.docx | heading, file name shown |
| 2 Checklist | extract, confirm | requirement text (safeguarding, social value) on screen; "Checklist confirmed (2 items" |
| 3 Evidence | upload 2 txt files | file names listed |
| 4 Draft | draft all | "[E-n]" marker on answer page; text contains "safeguarding" |
| 5 Claim check | check claims | "Ready to sign off" badge; Verdict column has "Supported"; no unsupported/contradicted/not checked |
| 6 Coverage/sign-off | read statement, tick, name, sign | Export button appears (gate opened) |
| 7 Export | download | .docx name; opens as valid zip; header "Draft prepared with AI assistance; reviewed by Alex Reviewer"; body has "safeguarding" and [E-n]; no page errors |

## Export-refused paths (backend, not e2e)
backend/tests/test_tender_export.py: test_export_refused_without_sign_off (409 export_blocked, no_signoff, no ExportRecord); test_reopen_voids_the_sign_off_and_export_is_refused (409 no_signoff, sign-off voided but kept); also refused after evidence delete and after answers changed; reopen-edit-sign-export; cross-tenant 404. test_tender_gate.py has an oracle test (every single flaw blocks). Covered, but not at browser level.

## Gaps (non-blocking; suggest follow-up task)
1. Step 2: e2e does not assert word limit, marks, mandatory flag or source-page link on the checklist, nor editing an item.
2. Step 3: no assertion of per-question retrieved evidence, nor the "nothing found" message.
3. Step 4: no word-limit assertion and no gap-marker path (NEEDS FIRM INPUT); fixtures give evidence for both questions.
4. Step 5: only the happy path in the browser; the blocked-by-unsupported-claim UI is not exercised (backend only).
5. Step 6: coverage table contents and the firm-responsibility statement text are not asserted (only that the field exists).
6. Step 7: footer text, limits shown, answer order and the evidence appendix are not asserted in the .docx.
7. No browser-level check that export is hidden or refused before sign-off or after reopen.
8. Fixtures are tiny (2 questions); unicode and long-input cases are absent.
