# Demo data sources

## D2: fictional firm name check (Companies House)

Method: public web search of the Companies House register and indexed company pages, company-level only. The search tool is a general web search, not the register's own search box, so it is indicative. A person can repeat the check at https://find-and-update.company-information.service.gov.uk/ before any public use.

| Date | Query | Result |
|---|---|---|
| 2026-11-27 | `Companies House "Brackenmoor Facilities" Ltd` | No record named "Brackenmoor Facilities". Near names only (Brambles House Facilities Limited, Brackenhurst Ltd 14658475). |
| 2026-11-27 | `Brackenmoor Limited company UK Companies House Brackenmoor` | No "Brackenmoor". Found **Brackenmore Ltd (05082830), active**, one letter different, plus Brackenmoss Limited (SC893978). Too close to a live company: rejected as confusable. |
| 2026-11-27 | `Companies House "Harrowmere Facilities" OR "Harrowmere Facilities Limited" OR "Harrowmere Services"` | No "Harrowmere" company found. Only unrelated "Harrow ..." and "Harrison Facilities Management Limited" names. Accepted. |

Decision: the fictional firm is **Harrowmere Facilities Ltd (fictional)**. SPEC.md section 5 updated to match. All identifiers in the evidence library are obviously made-up (CERT-DEMO-nnnn, "Company no. DEMO-0000"). Fictional clients are "Eastvale", "Marlowe Fen" and "Tarn Valley" councils; these are invented names and were not checked against real authorities, so they carry "(fictional)" on first use in each document.

## D1: tender packs

**Status: PARTIAL. 0 of 12 packs verified.** Twelve candidate packs were found and their notice data recorded, but none of their documents could be downloaded, so page counts, text checks and SHA-256 hashes are not done. No tender file is stored in the repo.

Why: on 2026-11-27 (about 18:30 to 18:35 UTC) every `/Notice/...` page and every `/Notice/Attachment/...` download on both Contracts Finder and Find a Tender returned **HTTP 403 from the site's own load balancer (`server: awselb/2.0`)**. This was not the studio's egress proxy. The search pages (`/Search`) and the Contracts Finder OCDS API (`/Published/Notices/OCDS/Search`) still returned 200. A WebFetch of a notice page also got 403. Retries over about two minutes were still blocked. The block was not worked around (no browser user-agent spoofing, no mirrors). It may be a WAF rule against cloud/automated clients, or a rate limit set off by the API scan. A later run, or a person in a browser, should try again.

Method: candidates come from the Contracts Finder OCDS search API (`stages=tender`, published 2023-01 to 2026-11, matched on notice titles). The only candidates kept are notices whose documents are attached on Contracts Finder itself (`/Notice/Attachment/...`), not on a third-party e-tendering portal. Small town and parish council notices were preferred because their packs are usually short. All data below comes from the API (accessed 2026-11-27).

Licence line (from the API response `license` field, applies to the notice data): `http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/`. Attribution to use: "Contains public sector information licensed under the Open Government Licence v3.0. Source: Contracts Finder, Cabinet Office." The **attached documents** were written by each buyer, and their licence has not been checked, because they could not be opened. Treat them as "licence unconfirmed": until a person confirms otherwise, store only the URL + SHA-256 + page count.

Access date for every row: 2026-11-27. "CF" = `https://www.contractsfinder.service.gov.uk`. Document URLs are `CF/Notice/Attachment/<id>`, with the format from the API in brackets.

| Pack | Sector | Buyer | Notice title | Notice URL | Document URL(s) | Access | Licence line | Pages | SHA-256 | Personal-data screening | In repo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P01 | Cleaning | Penzance Council | Penlee House Cleaning Contract 2025-2028 | CF/Notice/df4e6194-7f87-4cfe-b0e5-c67183fdd47d | 5ff90d9d-64d3-40d2-9164-936fa178e54f (pdf, Cleaning Specification); f95c9c12-6639-4e58-9b7b-4da30254af89 (xlsx, query log) | 2026-11-27 | OGL v3.0 (notice data); documents unconfirmed | not verified | not computed | not done (not downloaded) | no |
| P02 | Cleaning | Woodley Town Council | Cleaning Contract - Woodford Park Leisure Centre | CF/Notice/2239bb50-8e23-47b1-a21c-0658a1339e63 | 6234e3ee-5e15-45c9-8dcc-67402a3cb8e7 (docx); c06f2367-3ef5-414f-9d44-bf23eda6920f (pdf) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P03 | Cleaning | Syston Town Council | Syston Public Conveniences Cleaning Contract | CF/Notice/0ef154c2-e4c4-488c-b18c-d8ca7440db56 | 5c5e95ed-13e2-4ee7-809a-8bbf5ea9bf47 (pdf, bidding docs); 18ab49a5-f83e-453c-bfe2-37b2dfb621bd (pdf, illustration) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P04 | Cleaning | Bishops Cleeve Parish Council | Cleaning Contractor | CF/Notice/eb46726e-34b0-41bc-baac-d88dde36d2f6 | 11bd587f-fafa-430f-aa2e-f1c1034953e6 (doc, tender info + pricing schedule); 364849ac-b300-400c-a0f7-f76a3484d04a (pdf) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P05 | Security | The Coal Authority | HO - Manned Security Services | CF/Notice/1be51666-1e63-4a0c-aecf-9bcb10767e43 | bd3e66fb-389e-4427-b36c-2c52feefe3e1 (pdf); a2c6f357-fedd-4d27-99d3-fe3ff8102bcc (pdf) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P06 | Security | City College Plymouth | Security Services | CF/Notice/06b51f70-940a-45b3-9ae3-8c941f9e6048 | 4100d871-2b06-4d50-aac9-d0455a200a15, 2c76f224-377e-432d-a6ff-e1d83fb455d0, 3923672e-263c-4465-96ae-717a199167a7, 4be37e48-851b-4588-a60b-8ce20dedee48 (docx); bc0ce6c8-c25a-4f9a-af51-0aeefc0d2bd0 (xlsx); 0de8b5d5-960c-4ab8-ab56-bdfa1719e3b7 (pdf, clarifications) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P07 | Security | Ware Town Council | Security provision for Ware Priory Estate | CF/Notice/b5124078-4dd5-4680-af9e-9f23ec966221 | e22eca91-c0c3-42d8-8c9c-f09de704d66a (docx, security service spec) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P08 | Security (event security / stewarding) | Littlehampton Town Council | Event Security Services for Littlehampton Town Council 2026 - 2029 | CF/Notice/beb160e7-5c6f-483b-ac2b-be3a133aff20 | b5630741-155b-4558-b0f6-bbcaf9265e70 (pdf, tender notice); c1bfc20e-399a-413d-a584-29f60d5bbb44 (docx); 436ac98e-003b-4d19-8da8-dc198aae16d0 (docx, Q&A) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P09 | Grounds | Hawkinge Town Council | Grounds Maintenance Contract | CF/Notice/d8769b16-89f5-4d8e-9fd1-60d8b2ed8220 | aa4e7861-446d-4c0a-9587-227104bcc957 (docx, requirements + ITT); debb2aeb-772b-41f5-bb92-2ec82e4dd0b7, dd71c7ba-d0a3-4f0a-82be-041648f94aed (docx); 48ca386c-81e6-470f-9107-40cf47dd214d (xlsx); 42238815-2964-4602-a4e0-2768e4de44ef (doc); 24c16a64-4fc2-4ac8-9577-e17b33ad0b0e (pdf) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P10 | Grounds | West Mersea Town Council | Grounds Maintenance Contract 2026 | CF/Notice/c58b1fae-a010-479d-b028-3c1dc6808b55 | b92e179b-5cf8-4776-973d-07a5a231c105 (pdf, specification) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P11 | Grounds | Crediton Town Council | Crediton Grounds Maintenance Contract | CF/Notice/e2f3c016-77ee-4d4a-bca9-603d9f24f820 | c0b1323a-ae18-4df8-ad28-27f7759e13e2, 7dbfe979-2186-4035-9d8c-0e3d4467eb21, 568bafc1-a883-4a02-849b-d3b8c6ad8aa8, 3af424a4-5d86-4b1c-bf4b-d7a558edd716, b5b44437-6911-45b7-a774-a7f0656be3bc, 6fe89615-9639-4ef3-90e1-933728089f4e, 15f54f08-9a97-4b83-8b21-d360ab6df923 (all pdf) | 2026-11-27 | as P01 | not verified | not computed | not done | no |
| P12 | Grounds | Hythe Town Council | Grounds Maintanence [sic] | CF/Notice/6d6b9f4f-ccbd-41b3-a56f-ae7f12f4a656 | a48e66e7-466d-499d-ad5c-59a38fdc5303 (pdf, contract for all HTC sites) | 2026-11-27 | as P01 | not verified | not computed | not done | no |

### Roles (provisional, by the SPEC rule)

Packs in table order: P01, P02, P03, P04 (cleaning); P05, P06, P07, P08 (security); P09, P10, P11, P12 (grounds).

- **Demo packs (3): the LAST pack of each sector in table order:** P04 (cleaning), P08 (security), P12 (grounds).
- **Held-out packs (9): all the others:** P01, P02, P03, P05, P06, P07, P09, P10, P11.
- **Held-out drafting packs (SPEC section 3):** the rule is "the first pack of each sector in `demo-data/SOURCES.md` order". That gives **P01 (cleaning), P05 (security), P09 (grounds)**. All three are held-out packs, because the demo packs were set as the last of each sector.

These roles hold only once every pack passes verification. If a pack fails a check (over 40 pages, any image-only page, no open download, or a registration-only portal), remove its row, put a replacement from the same sector in the same position, and apply both rules again before any scored run. Write down every swap here.

### Still to do for D1

1. Download every document listed above without logging in. For each pack, record the total page count (DOCX pages from the rendered count or a page-count estimate, with the method stated) and the SHA-256 of each file.
2. Text check with `pypdf` / `python-docx` (run as `python3 -I` on files in a scratch directory): every page must have real text. Reject the pack if it has image-only pages or more than 40 pages in total.
3. Read each document for a licence or copyright line and record it. If none is found, store only the URL + SHA-256 + page count.
4. Personal-data screening for any derived `.txt` copy: replace a named individual's name, personal email or direct phone number with `[removed]`.
5. Fit notes: P05 (2023) and P06 (2023) are older notices, so their attachments may have been removed. P08 is event security, which is close to manned guarding but not the same. Spare candidates found in the same scan (documents on Contracts Finder): cleaning: Seaford Town Council toilet cleaning (ocds-b5fd17-5c3e7fd1-3213-42d5-8e2e-4d2177ae4daa), Lyme Regis Town Council multi-site cleaning (ocds-b5fd17-0d43bb80-07ae-42e3-995e-5cfae1cbd075); security: University of Salford "Building Security" (ocds-b5fd17-485190d6-2459-49e6-bcf9-200caba7b2c7), Northamptonshire Partnership Homes "Avenue Campus - Security Services" (ocds-b5fd17-dd090248-52b2-49fa-a571-79680b7958b7); grounds: Kirby Muxloe Parish Council (ocds-b5fd17-82fdeef7-f0cc-4099-a9b3-76587434f0de), Spratton Parish Council (ocds-b5fd17-fb815f92-4a06-4544-9389-82d443bc6c89), Redbourn Parish Council (ocds-b5fd17-a1bb33ac-833e-41dd-81c6-79f156aead0b).
6. Search gap: security packs with openly attached documents are rare on Contracts Finder. Most larger guarding contracts link to registration portals, and those are skipped.
