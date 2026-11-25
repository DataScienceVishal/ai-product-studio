"""Shared string types for request bodies. Postgres text cannot hold U+0000 (the insert fails with a 500), and
other control characters only cause trouble in logs and emails, so they are refused with a 422 at the edge."""
from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator

_LINE_BAD = re.compile(r"[\x00-\x1f\x7f]")  # any control character, newlines included
_TEXT_BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")  # control characters except \t \n \r


def _check(bad: re.Pattern, message: str):
    def check(value: str) -> str:
        if bad.search(value):
            raise ValueError(message)
        return value
    return check


def _strip(value):
    return value.strip() if isinstance(value, str) else value


# One line of text (names, titles, emails): no control characters at all.
SafeLine = Annotated[str, AfterValidator(_check(_LINE_BAD, "Remove control characters."))]
# Multi-line text (note bodies): tabs and newlines are fine.
SafeText = Annotated[str, AfterValidator(_check(_TEXT_BAD, "Remove control characters."))]
# A SafeLine stripped *before* length checks, so a blank value fails min_length.
StrippedLine = Annotated[str, BeforeValidator(_strip), AfterValidator(_check(_LINE_BAD, "Remove control characters."))]
