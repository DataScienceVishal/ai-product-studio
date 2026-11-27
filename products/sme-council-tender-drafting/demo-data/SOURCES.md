# Demo data sources

## D2: fictional firm name check (Companies House)

Method: public web search of the Companies House register and indexed company pages, company-level only. The search tool is a general web search, not the register's own search box, so it is indicative. A person can repeat the check at https://find-and-update.company-information.service.gov.uk/ before any public use.

| Date | Query | Result |
|---|---|---|
| 2026-11-27 | `Companies House "Brackenmoor Facilities" Ltd` | No record named "Brackenmoor Facilities". Near names only (Brambles House Facilities Limited, Brackenhurst Ltd 14658475). |
| 2026-11-27 | `Brackenmoor Limited company UK Companies House Brackenmoor` | No "Brackenmoor". Found **Brackenmore Ltd (05082830), active**, one letter different, plus Brackenmoss Limited (SC893978). Too close to a live company: rejected as confusable. |
| 2026-11-27 | `Companies House "Harrowmere Facilities" OR "Harrowmere Facilities Limited" OR "Harrowmere Services"` | No "Harrowmere" company found. Only unrelated "Harrow ..." and "Harrison Facilities Management Limited" names. Accepted. |

Decision: the fictional firm is **Harrowmere Facilities Ltd (fictional)**. SPEC.md section 5 updated to match. All identifiers in the evidence library are obviously made-up (CERT-DEMO-nnnn, "Company no. DEMO-0000"). Fictional clients are "Eastvale", "Marlowe Fen" and "Tarn Valley" councils; these are invented names and were not checked against real authorities, so they carry "(fictional)" on first use in each document.
