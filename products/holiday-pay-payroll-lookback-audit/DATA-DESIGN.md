# Pseudonymised data design (T-24, DRAFT for security sign-off, not legal advice)

```
 Payroll export (customer keeps the ID-to-person key)
   ▼
 ingest/loader.py: refuses personal and unknown columns
   ▼  worker_id, week_ending, element_category, amount
 engine/ + report/ (no network, no logs) ──► out/ files, 0600, customer keeps

 Distinct pay-element NAMES only ──► mapper ──► Azure OpenAI
                  a person confirms the table ◄──┘
```

## 1. Columns accepted and dropped at ingest

Only these columns are accepted (`ingest/loader.py:15-17`):

| File | Required | Optional |
|-|-|-|
| history.csv | worker_id, week_ending, element_category, amount | none |
| leave.csv | worker_id, week_ending | weeks |
| workers.csv | worker_id, worker_type | contract_weekly_basic, leave_year_start |

- Any other column is refused and nothing is written (`loader.py:116-118`, `audit.py:40-46`).
- Personal-looking headers are refused by name: name, NI, DOB, birth, address, postcode, email, phone, surname (`loader.py:31-32`, `94-96`, `113-114`).
- `worker_id` must be 1 to 64 safe characters (`loader.py:23`, `152-153`). One shaped like an NI number or a date is refused (`loader.py:62-77`, `150-151`). The check can be fooled (`EMPAB123456C`, see `ingest/FORMAT.md`).
- Rejected cells are masked to two characters and a length (`loader.py:80-85`).

## 2. Absences

- leave.csv has no reason column, so no reason can be given (`loader.py:16`, `116-118`).
- **Gap G1.** history.csv still has an `element_category` called `statutory`, with an amount (`engine/elements.py:13-14`). That says "SSP or SMP paid this week", and the flat SSP rate tells sickness apart from maternity. The engine uses `statutory` only as a yes/no marker (`engine/lookback.py:69`, `76-77`). *Proposed task:* replace it with a reason-free `excluded_week` marker with no amount. Results must not change: the golden tests stay identical.

## 3. What the mapper sends to Azure OpenAI

- The input file must have exactly `id, pay_element_name, source_style` (`mapper/run.py:97-102`). The extractor copies only those columns (`mapper/extract_names.py:16`, `29`).
- The request is the system prompt plus a JSON array of those three fields (`mapper/prompt.py:93-98`), sent from one place (`mapper/mapper.py:146`). No worker ID, date or amount goes out.
- The Responses call sets `store: false` (`mapper.py:273`). The endpoint must be https (`mapper.py:233`) and redirects are not followed (`mapper.py:55`).
- The audit never reads model output. Categories come only from the customer's own history.csv (`loader.py:207-209`), after a person confirms the table (`mapper/README.md`, "Limits").
- **Gap G2.** The extractor reads a labelled benchmark CSV, not a payroll export. *Proposed task:* an export-to-names extractor that outputs distinct names only and blocks names that look like a person or an NI number ("Bonus J Smith").
- **Gap G3.** Chat Completions doesn't send `store: false` (`mapper.py:277-280`). The deployment type isn't recorded (`_starter/DATA.md`, Processors), so names may be processed outside the UK and EU. *Proposed task:* record it, prefer DataZone EU or Regional, and send `store: false` on both APIs.

## 4. Storage region

- **Gap G4.** UK South isn't possible today. Azure for Students allows new resources only in five EU regions, so `rg-ai-studio` resources are in francecentral, though the group's metadata is in uksouth (`_starter/ADR/0002-azure-deploy.md:552-562`, `state/DECISIONS.md:175`).
- **Rule:** the studio subscription holds synthetic data only. Real data goes only to a pilot in the customer's own subscription in uksouth, set by `location` at handover.
- *Proposed task:* a uksouth handover param file, and a `SYNTHETIC_ONLY` switch: a banner, and no uploads unless the deploy is marked as a customer deploy.

## 5. Retention

- The CLI keeps only its two output files. No logging or network library is imported anywhere in `ingest/`, `engine/`, `report/` or `audit.py`.
- Outputs are created owner-only, mode 0600 (`report/builder.py:250`, `258`). The customer keeps them and decides when to delete.
- **Gap G5.** There is no hosted upload path yet, so nothing enforces the 30-day deletion. *Proposed task:* store uploads per tenant and delete them when the audit finishes, or within 30 days at most, using the starter's daily purge job (`_starter/DATA.md`). Disclose the 7-day database backups.

## 6. Logging

- **Rule:** no row data in any log: no worker_id, date, amount or pay-element name. Logs carry counts and token use only.
- In the CLI, errors go to stderr only, at most 50 (`audit.py:41-45`). The starter logs request, tenant and user IDs only (`_starter/backend/app/logs.py:1-4`), and Log Analytics keeps them 30 days.
- **Gap G6.** FORMAT.md says errors never print a full `worker_id`, but `loader.py:215`, `228`, `243`, `245`, `247`, `259`, `263` and `280` do. It is low risk, because the IDs are pseudonymous. *Proposed task:* mask them, or correct the doc.

## 7. Who can see what

| Who | Sees |
|-|-|
| Customer (bureau) | their own tenant's uploads and outputs |
| Other tenants | nothing |
| Studio | counts and token use only |
| Azure OpenAI | pay-element names only |

- Tenant isolation comes from the starter: re-test 3 passed (`_starter/SECURITY.md:3`), with 29 of 29 cross-tenant checks and every query scoped (`_starter/SECURITY.md:140-151`). The tenant comes from the session, not from the request (`_starter/backend/app/deps.py:38`).
- **Gap G7.** There is no hosted code yet. *Proposed task:* upload, audit and download routes on the starter, with cross-tenant tests copied from its sweep.

## 8. Residual risks

| Risk | Mitigation |
|-|-|
| Pseudonymised pay is still personal data, and small firms' workers can be singled out | Minimum columns, 30-day deletion, and a processor agreement reviewed by a lawyer before real data |
| An NI number is hidden inside an ID | The shape check, plus the customer's attestation at upload |
| SSP or SMP reveals health or family leave | G1 |
| A hostile or personal name reaches the model | Names only, the G2 filter, and a person confirms the table |
| Abroad processing, or Azure's abuse-monitoring retention | G3. Only names are sent |
| Real data on the Student subscription | G4 |
| Inputs are kept too long | G5 |
| A cross-tenant leak | Starter scoping, plus the G7 tests |
| Outputs are emailed unencrypted | 0600 files and the FORMAT.md warning. The hosted version is download-only |
| 16 and 17 year olds | No date of birth is taken |
