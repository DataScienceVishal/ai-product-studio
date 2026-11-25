# Round 18 scout summary (T-82, 2026-11-25)

Brief: edges-only (UK finance and tax, data engineering, RAG and agents), each candidate needing a dated 2026-2028 forcing function, 3 pain signals, 2 prices, a wedge checked on incumbents' own pages, and a self-run proof test under $5. About 17 minutes, 9 searches and 4 fetches. No prompt-injection attempts seen. Nobody contacted, nothing signed up for.

## Written (0 files)
No candidate survived the cheap kill test. Zero is the honest result.

## Dropped at the cheap kill test (candidate, forcing function, evidence, reason)

1. **Umbrella-company PAYE liability checks for agencies.**
   - Forcing function: real. From 6 April 2026 agencies (or end clients) are jointly and severally liable for PAYE in chains with an umbrella (https://www.gov.uk/guidance/paye-rules-for-labour-supply-chains-that-include-umbrella-companies-from-6-april-2026, search summary). GOV.UK expects "regular, reasonable and proportionate" checks, including payslips and reconciliation statements, and says not knowing "is not a defence" (https://www.gov.uk/guidance/responsibilities-for-employment-businesses-working-with-umbrella-companies, fetched 2026-11-25).
   - Kill: SafeRec already sells the whole job (fetched https://www.saferec.co.uk 2026-11-25): supplier checks, a drag-and-drop "Forensic Payslip Audit" with gross-to-net and NMW checks, an RTI cross-reference and a monthly check of the umbrella's HMRC tax account, KID generation, scoring and alerts. It is promoted through REC and APSCo member offers (search summaries, not fetched). No price on the page; REC lists certification as free to agencies (provider's claim, search summary). Fair Work Solutions covers NMW (see nmw-salaried-hours-audit kill). Pay could not be established (no price points).
2. **FRS 102 lease accounting for small companies (Section 20 changes, periods from 1 January 2026; first accounts mostly year ends 31 December 2026 and 31 March 2027).**
   - Forcing function: real and dated (FRC reminder, https://www.frc.org.uk/news-and-events/news/2026/09/frc-issues-reminder-of-significant-change-now-effective-in-uk-gaap/; ICAEW helpsheet; search summaries). Micro-entities are exempt.
   - Kill: the SMB tool layer exists. Lease102 is listed from £20 a month (SourceForge, search summary only, not page-verified); Finquery offers a free FRS 102 present-value calculator; Silverfin computes right-of-use values in its own product (https://support.silverfin.com/en/support/solutions/articles/101000576875-lease-liabilities-and-right-of-use-assets, summary); Netgain NetLease is marketed to UK and Irish SMEs (press release, no price). The core is a present-value schedule (deterministic), and some commentators say most small-company leases are operating leases so the impact is limited. Only the "read lease PDFs" step is AI, and that is the generic "AI reads documents" gap. A one-off transition job, so no basis for a subscription.
3. **Mandatory payrolling of benefits in kind (6 April 2027 for cars, vans, fuel and medical; most others April 2028).**
   - Forcing function: real (https://www.gov.uk/guidance/prepare-for-mandatory-payrolling-of-benefits-in-kind, search summary).
   - Kill: HMRC's own policy paper says software cost is expected to be "negligible" because payroll vendors build it in; IRIS, Sage and ADP already publish guidance. Deterministic arithmetic inside payroll software.
4. **Companies House software-only accounts filing, with P&L for small companies and no abridged accounts.**
   - Forcing function: real but moved to 1 April 2028 (ICAEW June 2026, https://www.icaew.com/insights/viewpoints-on-the-news/2026/jun-2026/companies-house-accounts-changes-confirmed-for-april-2028; gov.uk campaign page still says 2027, so it is stale).
   - Kill: every accounts-production product (Xero, FreeAgent, TaxCalc, IRIS, CCH, Sage) will file iXBRL; Companies House keeps a gov.uk list of compatible software. A tagging and filing job with no AI core, 17 months away.
5. **IHT on unused pensions from 6 April 2027 (estate asset schedule and IHT400 from document piles).**
   - Kill: Exizent (now Estatesearch), Cognito, LEAP, Shaw & Sons, The Wealthworks, FormEvo and Cloud Forms already sell IHT400 completion (https://www.gov.uk/government/publications/inheritance-tax-forms-commercial-software-suppliers, search summary); Probate Plus is £299 starter plus per-estate fees (Capterra UK, summary). It is also legal-adjacent (probate), and I did not confirm the April 2027 pensions rule from a page.
6. **R&D tax relief AIF drafting.** Forcing function is a simplification (claim notification form removed for claims from 1 April 2027, AIF simplified from autumn 2027), which reduces the job rather than creating one. No price found. Mostly sold by consultancies on a percentage of the claim, so there is no subscription analogue. Not pursued.
7. **CIS from 6 April 2026 (nil returns, tougher GPS, longer re-application bar).** Verification and nil returns are built into every CIS-capable payroll or accounts product (Beale Law advises checking the software "automatically generates NIL returns", search summary); HMRC's verify service is free. Deterministic. Dropped.
8. **Already-killed angles not repeated:** MTD for Income Tax bookkeeping categorisation (mtd-quarterly-prep), holiday-pay look-back (parked at 64, no new evidence this round).

## Lessons for the validator and next scout
- Every UK deadline I tested has a dated source but also an incumbent that was ready before the deadline: SafeRec (umbrellas), payroll vendors (benefits payrolling), accounts-production software (Companies House), probate-form vendors (IHT400). A forcing function that every vendor also sees is not a wedge.
- Where AI is the only new thing, the AI step is "read a document into a deterministic calculation" (lease terms, benefits values, estate assets). That is the pattern that lost in rounds 5, 8 and 10.
- The unsold space looks like it needs judgement over messy ledger data with no vendor-owned system of record (the holiday-pay look-back is still the nearest). This round found no second example.
- Pay evidence is the recurring hole: SafeRec, Netgain, Exizent and the IHT400 suppliers publish no price on the pages I could reach, so a 2-price-point test can't be met from search alone.
- Stop condition: after 8 UK deadlines with zero survivors, a further edges-only desk round is unlikely to help. The holiday-pay re-check (monthly) and buyer-side evidence (Q-9) are better uses of time.
