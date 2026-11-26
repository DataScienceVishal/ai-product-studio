"""Weekly-pay reference period average (gov.uk / ERA 1996 s.224)."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

PENNY = Decimal("0.01")
MAX_PAID_WEEKS = 52
MAX_LOOKBACK_WEEKS = 104


def dec(x) -> Decimal:
    """Decimal from int/str/Decimal; floats go via str() so binary noise never enters."""
    return Decimal(str(x)) if isinstance(x, float) else Decimal(x)


def money(x) -> Decimal:
    """Round to the penny, half up (published rounding)."""
    return dec(x).quantize(PENNY, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ReferenceResult:
    weeks_used: int          # paid weeks in the average
    weeks_scanned: int       # calendar weeks looked at (<= 104)
    weeks_skipped: int       # no-pay weeks skipped, counted only up to the point 52 paid weeks were found
    total: Decimal
    average: Decimal         # unrounded
    shortened: bool          # fewer than 52 paid weeks found
    indices: tuple = ()      # 0-based positions (0 = most recent week) of the weeks used

    @property
    def average_rounded(self) -> Decimal:
        return money(self.average)


def reference_average(weekly_pay_recent_first: Sequence, max_paid: int = MAX_PAID_WEEKS,
                      max_lookback: int = MAX_LOOKBACK_WEEKS) -> ReferenceResult:
    """Average weekly pay over up to `max_paid` weeks that had pay.

    Input is weekly pay, most recent complete week first (the week before the
    leave). A week with any pay > 0 counts; weeks with no pay are skipped and
    counting goes back further, but never beyond `max_lookback` weeks. If fewer
    than `max_paid` paid weeks exist the average uses those available.
    Zero paid weeks gives average 0.
    """
    total = Decimal(0)
    used = skipped = scanned = 0
    idx = []
    for pos, pay in enumerate(weekly_pay_recent_first[:max_lookback]):
        pay = dec(pay)
        scanned += 1
        if pay < 0:
            raise ValueError("negative weekly pay")
        if pay == 0:
            skipped += 1
            continue
        total += pay
        used += 1
        idx.append(pos)
        if used == max_paid:
            break
    avg = total / used if used else Decimal(0)
    return ReferenceResult(used, scanned, skipped, total, avg, used < max_paid, tuple(idx))
