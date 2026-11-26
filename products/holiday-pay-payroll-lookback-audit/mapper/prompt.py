"""The mapper's system prompt, written from first principles (not tuned on any labels).

Basis: Working Time Regulations 1998 reg 13/13A (as amended from 1 Jan 2024 for irregular-hours and part-year workers),
the Employment Rights Act 1996 ss 221-224 (what counts in a week's pay), and gov.uk "Calculate holiday pay".
"""
from __future__ import annotations

import hashlib

PROMPT_VERSION = "mapper-prompt-v1"

CATEGORIES = (
    "basic", "regular_overtime", "commission", "bonus_non_regular", "allowance",
    "expense_excluded", "holiday_pay_paid", "statutory_excluded", "deduction_excluded",
)

DEFINITIONS = {
    "basic": "Ordinary pay for contracted hours: salary, wages, hourly or day rate, standard pay for hours worked.",
    "regular_overtime": "Pay for hours beyond contract that the worker is required or regularly does: overtime, extra hours, "
                        "premium rates for those hours (time and a half, double time), shift premiums for extra hours.",
    "commission": "Pay that varies with sales or results: commission, sales incentives, piece-rate or results-based pay "
                  "that is earned regularly as part of normal pay.",
    "bonus_non_regular": "Discretionary or one-off payments not tied to normal working: annual or Christmas bonus, "
                         "ex-gratia, golden hello, retention or referral bonus, long-service gift.",
    "allowance": "Regular contractual supplements linked to the job, status, length of service or working pattern: "
                 "shift or on-call allowance, London weighting, seniority or professional-status payments, "
                 "responsibility, first-aider or standby allowance.",
    "expense_excluded": "Reimbursement of costs and benefits that are not pay for work: expenses, mileage, travel, "
                        "subsistence, uniform or phone allowance as reimbursement, benefits in kind, redundancy or "
                        "notice payments, loan advances.",
    "holiday_pay_paid": "Pay already given for annual leave: holiday pay, annual leave, bank holiday pay, "
                        "accrued holiday paid out, rolled-up holiday pay.",
    "statutory_excluded": "Statutory payments from the employer that are not normal pay: SSP, SMP, SPP, ShPP, SAP, "
                          "statutory sick, maternity, paternity, adoption or parental bereavement pay, and "
                          "occupational sick or maternity top-ups.",
    "deduction_excluded": "Anything taken off or not gross pay: income tax (PAYE), employee or employer NI, pension "
                          "contributions, student loan, attachment of earnings, union fees, salary sacrifice, "
                          "other deductions, and net pay or total lines.",
}

_RULES = """You classify payroll pay-element names (as they appear on payslips and payroll reports from UK payroll
software) into exactly one holiday-pay category. This is for checking holiday pay under the UK Working Time Regulations
reg 13 and 13A as amended in 2024 and gov.uk "Calculate holiday pay".

Why the categories matter: normal pay for holiday includes basic pay, regular overtime, commission, and payments linked
to length of service or professional status. One-off or discretionary bonuses are usually not included. Expenses,
benefits, statutory payments and deductions are not normal pay. Holiday pay already paid must be recognised so it is
not counted as normal work pay.

Categories (use these ids exactly):
{definitions}

Guidance:
- Judge by the meaning of the name, not by spelling or abbreviation. Names may be abbreviated (OT, Comm, Hol, NI, SSP),
  misspelt, in upper case or carry rate or period text.
- If a name is genuinely ambiguous, choose the single most likely category. Never invent a new category and never
  leave a name out.

Output: reply with ONLY a JSON array, no prose and no code fences. One object for every input item, in the same order,
each of the form {{"id": "<the id exactly as given>", "category": "<one category id>"}}."""

SYSTEM_PROMPT = _RULES.format(definitions="\n".join(f"- {c}: {DEFINITIONS[c]}" for c in CATEGORIES))
PROMPT_SHA256 = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()


def build_user_message(rows: list[dict]) -> str:
    """The names to classify, as a JSON array of {id, pay_element_name, source_style}. Nothing else is sent."""
    import json
    items = [{"id": r["id"], "pay_element_name": r["pay_element_name"], "source_style": r.get("source_style", "")}
             for r in rows]
    return "Classify these pay elements:\n" + json.dumps(items, ensure_ascii=False)
