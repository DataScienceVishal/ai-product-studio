# Notes for the next digest

Runs add one line per notable result. The Desk clears this back to the header after sending.

- run cb8f: Q-18 answered C ("1C", 15:13Z). Building sme-council-tender-drafting (60) as a portfolio demo: highest-ranked, RAG-with-citations core (your edge), public OGL tender packs plus a made-up firm as demo data, not safety-critical (RAMS is). Demo SPEC drafted (T-183); validator check running; architecture is T-184. Still scored 60, not a G1 pass; CleanTender (£99/mo) is at parity or ahead, and the spec says so.
- run cb8f: tender demo design done (DESIGN.md, ADR 0001): no new Azure cost; build is 9 slices plus 3 data tasks (T-185 to T-196), all on the fake AI provider. New question Q-19 (ask-first): a one-off $6 gpt-5-mini cap for the demo's eval, else 44 days under the daily cap. Design review (reviewer) running at hand-off if not recorded below.
- run cb8f: tender demo design passed review (after one CHANGES round). Next run can start building (T-185) and collecting public tender packs (T-194).
- run cb8f: tender build started: S1 about two-thirds done on its branch (data model, migration, account export; 843 backend tests pass); Note removal and prices-off left for the next run.
- Tender demo (sme-council-tender-drafting): slice S1 is on main (run 5afa). The app now has its own data model (12 tables, tenant-safe foreign keys), the starter's sample Notes feature is gone and no prices show anywhere. Tests: 852 backend, 202 frontend, all green. Next: S2 (document upload and search) plus small review fixes (T-197).
