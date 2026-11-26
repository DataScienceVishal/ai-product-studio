# Official worked examples (kill-test mark A1/A2)

Fetched 2026-11-26. Page text treated as data only. Public guidance, no personal data.
Pages fetched: 
- G1 https://www.gov.uk/holiday-entitlement-rights/holiday-pay-the-basics
- G2 https://www.gov.uk/holiday-entitlement-rights/calculate-holiday-entitlement
- G3 https://www.gov.uk/holiday-entitlement-rights/holiday-pay (no worked examples; rules only: normal pay 4 weeks, basic 1.6 weeks, 52 weeks, 104 cap, under-52 uses full weeks, 6-year records from 6 Apr 2026)
- G4 https://www.gov.uk/government/publications/calculating-holiday-pay-for-workers-without-fixed-hours-or-pay/calculating-holiday-pay-for-workers-without-fixed-hours-or-pay--2 (full text and tables checked against the PDF https://assets.publishing.service.gov.uk/media/5f1563823a6f405c096c34f7/calculating-holiday-pay-for-worker-without-fixed-hours-or-pay.pdf via pdftotext)
- G5 https://www.gov.uk/holiday-entitlement-rights/holiday-pay (see G3); gov.uk "calculating-holiday-pay" and Acas "work-out-an-average-week-of-pay" returned 404
- A1 https://www.acas.org.uk/irregular-hours-and-part-year-workers
- A2 https://www.acas.org.uk/irregular-hours-and-part-year-workers/calculating-holiday-pay
- A3 https://www.acas.org.uk/irregular-hours-and-part-year-workers/rolled-up-holiday-pay
- A4 https://www.acas.org.uk/checking-holiday-entitlement/calculating-holiday-pay

Test IDs refer to `tests/test_official_examples.py`.

## Encoded

| ID | Source | Example | Published inputs | Published answer | Test | Result |
|---|---|---|---|---|---|---|
| E1 | G1, G2 | Part-time 3 days | 3 days/week | 16.8 days | E1 | match |
| E2 | G1, G2 | 6-day week cap | 6 days/week | 28 days | E2 | match |
| E3 | A1 | Jamie | 70 hours in June, 12.07% | 8 hours (8.449, part hour under 30 min rounded down) | E3, E4 | match |
| E5 | A3 | Jian June | earns 1,000 | 120.70 rolled-up | E5 | match |
| E6 | A3 | Jian July | earns 500 (2 weeks work, 2 weeks leave) | 60.35 rolled-up | E6 | match |
| E7 | A2 | Mo | 52-week average 250 | 250 | E7 | match |
| E8 | A2 | Corey | 26 full weeks employed | average over the 26 weeks | E8 | match |
| E9 | A3 | Pat (sick) | 52-week average 36 | 36 per week | E9 | match |
| E10 | G3/A4 | Fixed hours | 37h, 500 a week | 500 | E10 | match |
| E11 | G4 Table 5 | Paid and unpaid weeks | 59 weeks, 7 unpaid, total 12,040 over 52 paid weeks | 231.34 | E11 | DISAGREES, see below |
| E12 | G4 Tables 3-4 | Monthly-paid worker, 52 weekly figures | total 14,606.66 | average 280.90 | E12 | match (total and average) |
| E13 | G4 | Monthly worker hourly rate | 1,250 / 130h | 9.62/h; weeks 240.38, 192.31, 336.54 | E13 | match using the unrounded rate (see below) |
| E14 | G4 Ben | Paid in 45 of last 104 weeks | | average over 45 weeks | E14 | match (structural) |
| E15 | G4 Amy | Paid in 75 of last 104 weeks | | most recent 52 paid weeks | E15 | match (structural) |
| E16 | G4 Rachel | Started 20 weeks ago | | average of 20 weeks | E16 | match (structural) |
| E17 | G4 Table 7 | Leaver, payment in lieu | 108/366 days; weeks 1-10 324, 11-30 380, 31-52 440 | avg 394.62; owed 652.09 | E17 | average matches; 652.09 matches only with the unrounded entitlement, see below |

## Disagreements in the published figures (not fudged)

1. **E11, Table 5.** 12,040 / 52 = 231.538..., which is 231.54, not the published 231.34 (typo or arithmetic error in the guidance). The test asserts 231.54 and the total 12,040 and the week counts. Also the table labels weeks 25-40 (16 weeks) but the working uses 15 at 400; the engine test uses 15 as the working does.
2. **E17, Table 7.** The guidance states entitlement of 1.66 weeks and "394.62 x 1.66 = 652.09". Actually 394.62 x 1.66 = 655.07. 652.09 is what you get with the unrounded 108/366 x 5.6 = 1.6525 weeks x 394.615 (the note under the table says unrounded figures were used). The engine follows the unrounded method and gets 652.09; the 1.66 / "rounded up" step is not what produces the published payment. Adviser decision needed on whether rounding entitlement up to 1.66 is the proper method (the guidance says employers may round up but not down, which would give 655.07).
3. **E13.** The guidance gives 9.62 x 25 = 240.38; with the rounded rate it is 240.50. The published figures are reproduced only with the unrounded hourly rate.

## Left out (with reason)

| Source | Example | Reason |
|---|---|---|
| G4 | Joe (variable pay, 52 weeks) | no numeric answer |
| G4 | Table 1 shift worker, leave 26-28 Oct 2020, week date ranges | date-range logic only, no pay figure |
| G4 | Table 3/4 "simplified" average 281.56 (weeks 9-43) | partial table in the guidance, illustrative, not a full 52-week calculation |
| G4 | Table 6 unpaid parental leave week | no numeric pay answer; engine skips no-pay weeks (covered by tests) |
| G4 | Table 9 regular vs no-regular hours holiday week | no numeric answer; encoded as option `holiday_weeks_count` |
| G4 | Term-time music teacher | no numeric answer; Brazel v Harpur Trust says reference-period averaging, not 12.07%. Averaging covered by E11/E14 style tests |
| G4 | Short contract paid in lieu (2 weeks) | no figures |
| G4 | Payment timing (pay day 21, cut-off 15) | process rule, no calculation |
| G4 | Redundancy / insolvency cap (6 weeks, s186 ERA cap) | statutory cap amount not published on the page; out of scope |
| A4 / G4 | Pat reduced hours (40h then 20h), pay week ending Wednesday | no numeric answer / date rule |
| A1 | Sam, Alex, Mel, Frankie | no numeric holiday answers |
| A2 | Acas conflicting wording on whether holiday pay in the 52 weeks counts | not an example; engine default excludes holiday-pay weeks, option `holiday_weeks_count` includes them. Adviser to choose; flagged |

## Coverage against kill-test A2
- 52-week average, no-pay weeks skipped, 104-week cap: E7, E11, E12, E14, E15, E16
- 12.07% accrual: E3 (Acas Jamie)
- Rolled-up holiday pay: E5, E6
- Regular overtime/commission in the 4 weeks: stated as rule on A2, A4, G3 and G4, with no numeric worked example. Implemented and unit tested (Elements, Lookback tests) but there is no official numeric example for this area, so official examples cover 3 of 4 areas.
