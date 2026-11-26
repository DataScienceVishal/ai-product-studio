# T-24 security gate: pseudonymised data design

Reviewer: security agent, 2026-11-26. Reviewed: `DATA-DESIGN.md` (T-24), the validator's item 4 in `state/ideas/holiday-pay-payroll-lookback-audit.md`, and the code it cites. Product code was not changed. DRAFT, not legal advice.

## Verdict: PASS (design sign-off for the current stage: offline CLI, synthetic data only)

This verdict covers the design only. Validator item 4 is met **as a design**. In code it is only partly met: payroll ID only is enforced; "excluded week, no reason" waits on G1; the UK region waits on G4 and the handover; 30-day deletion waits on G5. The Risk score should go to 7 only for a product that ships with the conditions below. The conditions are split into two sets: before a hosted MVP, and before any real payroll data.

## 1. "Already enforced" claims, checked against the code

| Claim | Evidence | Result |
|-|-|-|
| Column allow-list per file | `ingest/loader.py:15-17`; any other header is refused at `116-118`, and missing or duplicate columns at `119-126` | Confirmed |
| Nothing is written when a check fails | `audit.py:38-46`: a ValidationError prints at most 50 issues to stderr and returns 2 before `write_outputs` | Confirmed |
| Personal headers refused by name | `loader.py:31-32`, `94-96`, `113-114`. Probe: "Worker Name", "forename" and "NI No" are refused. "National Ins", "sort_code" and "bank" are not matched by name, but the allow-list refuses them anyway | Confirmed (the allow-list is the real control) |
| worker_id shape, NI and date refusal | `loader.py:23`, `62-77`, `146-156`. Probe: `AB123456C`, `ab-12-34-56-c` and `EMP_AB_123456_C` are refused. `EMPAB123456C` is accepted, as `FORMAT.md` documents | Confirmed, with a known bypass |
| Rejected cells masked | `loader.py:80-85`, used for date, amount, category, type and leave_year_start | Confirmed (worker_id is the exception, see G6) |
| leave.csv has no reason column | `loader.py:16`, and the allow-list | Confirmed |
| `statutory` used only as a yes/no marker | `engine/lookback.py:69`, `76-77` are its only uses (`grep` of engine/, report/, audit.py); `engine/elements.py:13-14` | Confirmed, so G1 can drop the amount without changing results |
| Mapper sends names only | `mapper/run.py:97-103` requires exactly `id,pay_element_name,source_style`; `extract_names.py:16`, `29` copy only those; `prompt.py:93-98` builds the only user message; `mapper.py:146` is the only call site | Confirmed |
| `store: false`, https only, no redirects | `mapper.py:273-274` (Responses only), `232-233`, `54-61` | Confirmed. The Chat payload at `277-280` has no `store` (G3). The docstring at `mapper.py:218-220` does not claim it |
| Audit never reads model output | Categories come only from history.csv `element_category`, checked against `CATEGORIES` (`loader.py:207-209`) | Confirmed |
| No logging or network imports in ingest/, engine/, report/, audit.py | `grep` for logging, socket, http, urllib, requests, ssl and smtp imports finds nothing | Confirmed |
| Outputs are mode 0600 | `report/builder.py:250` (docstring) and `258` (`tempfile.mkstemp`, which creates files with 0600) | Confirmed |
| Starter tenant isolation | `_starter/SECURITY.md:3` (re-test 3 PASS) and `140-151` (29/29 cross-tenant sweep); `_starter/backend/app/deps.py:30-41` gets the tenant from the session row | Confirmed |
| Starter logs IDs only | `_starter/backend/app/logs.py:1-4` | Confirmed |
| Region facts | `_starter/ADR/0002-azure-deploy.md:552-562` and `state/DECISIONS.md:175` (francecentral; the group's metadata is in uksouth) | Confirmed |

Tests: `python3 -m unittest discover -s tests` ran **329 tests, OK** (47.6 s). pytest is not installed in this environment.

## 2. Gaps: which block what

### Must be done before a hosted MVP (G3 gate), even on synthetic data

- **G7.** Upload, audit and download routes on the starter. Copy the cross-tenant sweep (B reads, downloads and deletes A's upload and output, and gets a 404 each time), and add tests that object names and paths come from the server, never from the request (path traversal).
- **G5.** Per-tenant upload storage. Delete inputs when the audit finishes, with a purge job as a backstop at 30 days or less. Add a test that the purge removes both the blob and its database row. Write the 7-day backup window into DATA.md.
- **G4 switch.** A `SYNTHETIC_ONLY` flag, on by default in the studio subscription: a visible banner, and uploads refused unless the deploy is marked as a customer deploy. Storage private (no public blob access, SAS links short-lived or none), and download only through the authenticated route.
- **G6.** Mask `worker_id` in the error messages at `loader.py:215`, `228`, `243`, `245`, `247`, `259`, `263` and `280`, or correct FORMAT.md line 8. This is cheap. In a hosted product these messages reach the browser and probably the logs, so fix it with G7.
- **Logging rule test.** Add a test that pushes a fixture through the hosted routes and asserts that no worker_id, date, amount or element name appears in the captured logs.

### Must be done before any real payroll data (pilot), whoever hosts it

- **G1.** Replace `statutory` with an `excluded_week` marker that carries no amount, and keep the golden tests identical. This is what validator item 4 actually asks for, and it removes the SSP/SMP rate signal, which is health-adjacent and family data. It is small enough to do now in the CLI.
- **G2.** An extractor from a real export that outputs distinct names only and blocks names that look like a person or an NI number. Without it, a real payroll element such as "Bonus J Smith" goes to the model.
- **G3.** Record the Azure OpenAI deployment type for the mapper model. Use Regional or DataZone EU, not Global Standard. Send `store: false` on the Chat API as well, or pin the mapper to Responses. Note that Azure's abuse monitoring can keep prompts for up to 30 days unless an exemption is approved. Only names are sent, but the customer must be told.
- **Handover.** A uksouth param file, a processor agreement (Article 28) reviewed by a lawyer, and an upload attestation: "IDs are pseudonymous; you keep the key".

### Fine to defer

- The bypass via an NI number glued to a prefix (`EMPAB123456C`). It is documented, the attestation covers it, and a stricter check would refuse real payroll IDs.
- **New, low (call it G8).** A worker_id can still be name-shaped, such as `john.smith` or `JSmith1990` (probe: both accepted). No regex can fix this reliably. Defer: say so in FORMAT.md and the attestation, and consider an optional customer-side helper that replaces IDs with a keyed hash before upload.

## 3. G4: is an EU region acceptable for UK payroll data?

- **Legally, yes.** A UK controller sending personal data to France is not a restricted transfer that needs IDTA paperwork. The UK's adequacy regulations (DPA 2018, Schedule 21, para 5) cover EEA states. Pseudonymised payroll data is still personal data, so UK GDPR applies in full. DRAFT, not legal advice: confirm with the lawyer reviewing the processor agreement.
- **The design is stricter than the law, and that is correct.** Real data never goes on the Azure for Students subscription, for three reasons: the subscription switches off when the credit runs out, it is the studio's account and not the customer's, and the customer would not control deletion. For that reason the EU region only ever holds synthetic data, and the question matters in practice only if a later decision lets the studio host a pilot.
- **What the customer must be told:**
  1. where the data is stored and processed: the region of storage, compute and database, and the Azure OpenAI deployment type and its geography;
  2. that Microsoft is a sub-processor, the abuse-monitoring retention, and that only pay-element names are sent to the model;
  3. retention: inputs deleted within 30 days or less, plus 7 days of backups;
  4. that many bureaux' own client contracts promise UK hosting. If theirs do, they need the uksouth handover deployment, not an EU one.

Put these in the processor agreement, the sub-processor list and the DRAFT privacy notice.

## 4. Board tasks for the Studio Lead to open

All sections pass, so no task here comes from a FAIL. These are the conditions above:

1. G1, `excluded_week`
2. G2, names extractor
3. G3, deployment type and `store`
4. G4, `SYNTHETIC_ONLY` switch and uksouth param
5. G5, upload purge
6. G6, mask worker_id
7. G7, hosted routes and cross-tenant tests
8. G8 note in FORMAT.md

**Urgent: none.** Nothing is deployed, and no real data or secrets are involved.
