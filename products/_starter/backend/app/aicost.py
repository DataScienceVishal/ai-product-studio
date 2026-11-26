"""AI cost guard (T-91): what the daily token cap costs at the price of the model that is actually deployed.

Used in two places with one rule: the app refuses to start (config.py) and `infra/cost-guard.sh` refuses to deploy
(it runs this file: `python3 -I aicost.py check ...`) when

    worst-case monthly cost = AI_GLOBAL_DAILY_TOKENS x 31 x price per million tokens / 1,000,000

is above AI_MONTHLY_BUDGET_USD. Only AI_GLOBAL_DAILY_TOKENS is used: every call is checked against it before it runs
(ai.py, reserve), so it bounds all tenants together, whatever the per-tenant caps add up to.

Standard library only, so the deploy workflow can run it without installing the app. It never prints the deployment
name or any key: the deployment name comes from a secret in the deploy workflow.
"""
from __future__ import annotations

import argparse
import math
import re
import sys

# The Azure OpenAI line in state/BUDGET.md (Vishal approved at most $6.10 a month; the default 98,000 tokens x $2.00 per
# million x 31 days = $6.08) is the default. The studio's whole Azure credit is $80
# (CLAUDE.md section 10); raising this needs Vishal's approval.
DEFAULT_MONTHLY_BUDGET_USD = 6.10
DAYS_PER_MONTH = 31  # the longest month, so the figure is a true worst case

# Blended USD per million tokens, by deployment name (lower case, exact match). These are ESTIMATES, checked
# 2026-11-25 (Global deployments; Data Zone and Regional ones list about 10% higher, not modelled), from the vendors' list prices as recorded in state/BUDGET.md (OpenAI model pages, Microsoft Foundry
# launch posts). Each figure is the OUTPUT price, which is what a capped token costs at worst (reasoning tokens
# bill as output), so the blend is conservative. gpt-5.4-pro is $30 in / $180 out: 180 is the conservative figure.
# An agreement or a different region can change real prices; the Azure spend report is the final word. A deployment
# name Azure lets you choose freely, so a renamed deployment is "unknown" until AI_PRICE_PER_MILLION_TOKENS says
# what it costs.
MODEL_PRICES_PER_MILLION: dict[str, float] = {
    "gpt-5-nano": 0.40,
    "gpt-5-mini": 2.00,
    "gpt-5": 10.00,
    "gpt-5-pro": 120.00,
    "gpt-5.4-pro": 180.00,
}


def parse_price(value: object) -> float:
    """A price in USD per million tokens: finite and above 0, or ValueError."""
    try:
        price = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"AI price is not a number: {value!r}") from None
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"AI price must be a finite number above 0, got {value!r}")
    return price


def resolve_price(deployment: str, explicit_price: object = None) -> float:
    """For a deployment in the table: the larger of the table price and the explicit price, so an explicit setting
    can raise the price but never lower it (lowering needs a reviewed change to the table). For an unknown
    deployment: the explicit price, or ValueError."""
    explicit = None
    if explicit_price is not None and str(explicit_price).strip() != "":
        explicit = parse_price(explicit_price)
    known = MODEL_PRICES_PER_MILLION.get((deployment or "").strip().lower())
    if known is not None:
        return known if explicit is None else max(known, explicit)
    if explicit is not None:
        return explicit
    raise ValueError("the AI deployment is not in the price table (app/aicost.py): set AI_PRICE_PER_MILLION_TOKENS "
                     "to its blended USD price per million tokens, using its output price to be safe")


_DATE_SUFFIX = re.compile(r"-([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{8})$")  # ASCII digits only


def reported_model_price(model: object) -> float | None:
    """Table price of the model a provider says it ran (T-100 M1), or None when it is not in the table.
    Lower-cases, drops ONE trailing date (`gpt-5.4-pro-2026-03-05` -> `gpt-5.4-pro`) and then needs an exact table name.
    Any other suffix makes it a different model (T-162): `gpt-5-mini-pro` is unknown, not priced as `gpt-5-mini`, and
    `gpt-5.4` is unknown, not priced as `gpt-5`. Unknown fails closed in ai.py (AI off unless a price is set)."""
    if not isinstance(model, str):
        return None
    return MODEL_PRICES_PER_MILLION.get(_DATE_SUFFIX.sub("", model.strip().lower(), count=1))


def monthly_cost(daily_tokens: int, price: float) -> float:
    return daily_tokens * DAYS_PER_MONTH * price / 1_000_000


def check_ai_budget(deployment: str, explicit_price: object, daily_tokens: object, budget: float) -> float:
    """Worst-case monthly cost, or ValueError when it passes the budget (or an input is unusable)."""
    try:
        tokens = float(daily_tokens)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"AI cap or price is not a number: tokens={daily_tokens} price={explicit_price}") from None
    if not math.isfinite(tokens) or tokens <= 0:
        raise ValueError(f"AI cap and price must both be above 0: tokens={daily_tokens} price={explicit_price}")
    try:
        price = resolve_price(deployment, explicit_price)
    except ValueError as exc:
        if "not a number" in str(exc):
            raise ValueError(f"AI cap or price is not a number: tokens={daily_tokens} price={explicit_price}") from None
        if "above 0" in str(exc):
            raise ValueError(f"AI cap and price must both be above 0: tokens={daily_tokens} price={explicit_price}") from None
        raise
    if not math.isfinite(budget) or budget <= 0:
        raise ValueError(f"AI_MONTHLY_BUDGET_USD must be a finite number above 0, got {budget!r}")
    cost = monthly_cost(tokens, price)  # type: ignore[arg-type]
    if cost > budget:
        raise ValueError(f"{daily_tokens} tokens a day x ${price:g} per million x {DAYS_PER_MONTH} = ${cost:.2f} a month, "
                         f"over the ${budget:.2f} AI budget (AI_MONTHLY_BUDGET_USD). Lower AI_GLOBAL_DAILY_TOKENS "
                         f"to at most {int(budget / (DAYS_PER_MONTH * price) * 1_000_000)}, or have Vishal raise the budget")
    return cost


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="aicost.py")
    parser.add_argument("command", choices=["check"])
    parser.add_argument("--deployment", default="")
    parser.add_argument("--price", default="")
    parser.add_argument("--tokens", required=True)
    parser.add_argument("--budget", default=str(DEFAULT_MONTHLY_BUDGET_USD))
    args = parser.parse_args(argv)
    try:
        cost = check_ai_budget(args.deployment, args.price, args.tokens, float(args.budget))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"AI cost ok: ${cost:.2f} a month within ${float(args.budget):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
