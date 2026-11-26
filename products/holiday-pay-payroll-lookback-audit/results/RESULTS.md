# Kill-test Part B results

- Gold sha256 (verified equal to the expected value): `6323f7fbfad3c358223840452c08e973a0b41fa431a68d98f936a27d17c7669d`
- Run: live, model `gpt-5-mini`, deployment `gpt-5-mini`, 2026-11-26T21:20:42Z
- Prompt: mapper-prompt-v2 sha256 `ae175fa9c2fa89f244dba58854abe9ea0739d86ea35cfe9a917b746b88a4a5ed`
- Tokens: 5738 in, 2222 out, cost $0.0059

## Headline: nine-category accuracy 92.5% (200 names)

Eight-category accuracy (deduction_excluded folded into expense_excluded on both sides): 93.5%. The nine-category figure is the headline and the one B1 is judged on.

| Subset | Names | Nine-category accuracy |
|---|---|---|
| Rows marked AMBIGUOUS | 32 | 71.9% |
| All other rows | 168 | 96.4% |

UNMAPPED (invalid or missing, counted wrong): 0
Rows noted AMBIGUOUS: 32 (prefix `AMBIGUOUS:`, case-sensitive)

## Per category

| Category | Support | Predicted | Precision | Recall |
|---|---|---|---|---|
| basic | 28 | 28 | 100.0% | 100.0% |
| regular_overtime | 24 | 24 | 100.0% | 100.0% |
| commission | 20 | 19 | 100.0% | 95.0% |
| bonus_non_regular | 22 | 23 | 95.7% | 100.0% |
| allowance | 24 | 31 | 77.4% | 100.0% |
| expense_excluded | 20 | 16 | 87.5% | 70.0% |
| holiday_pay_paid | 16 | 16 | 100.0% | 100.0% |
| statutory_excluded | 24 | 18 | 100.0% | 75.0% |
| deduction_excluded | 22 | 25 | 80.0% | 90.9% |

## Confusion (rows gold, columns predicted)

| gold \ pred | basic | regular_overtime | commission | bonus_non_regular | allowance | expense_excluded | holiday_pay_paid | statutory_excluded | deduction_excluded | UNMAPPED |
|---|---|---|---|---|---|---|---|---|---|---|
| basic | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| regular_overtime | 0 | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| commission | 0 | 0 | 19 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| bonus_non_regular | 0 | 0 | 0 | 22 | 0 | 0 | 0 | 0 | 0 | 0 |
| allowance | 0 | 0 | 0 | 0 | 24 | 0 | 0 | 0 | 0 | 0 |
| expense_excluded | 0 | 0 | 0 | 0 | 6 | 14 | 0 | 0 | 0 | 0 |
| holiday_pay_paid | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 0 | 0 | 0 |
| statutory_excluded | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 18 | 5 | 0 |
| deduction_excluded | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 20 | 0 |

## Verdicts

- B1 (nine-category accuracy 92.5%, PASS needs >= 95%): **KILL**
- B2 (cost per 200 names $0.0059; PASS < $0.02, KILL > $0.05, else REVIEW): **PASS**

