"""Shared string types for request bodies. Postgres text cannot hold U+0000 (the insert fails with a 500), and
other control characters only cause trouble in logs and emails, so they are refused with a 422 at the edge."""
from __future__ import annotations

import re
import unicodedata
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator

LINE_BAD = re.compile(r"[\x00-\x1f\x7f]")  # any control character, newlines included
_TEXT_BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")  # control characters except \t \n \r


def _check(bad: re.Pattern, message: str):
    def check(value: str) -> str:
        if bad.search(value):
            raise ValueError(message)
        return value
    return check


def _invisible(value: str) -> bool:
    """True when the text is only whitespace and invisible format characters (category Cf: zero-width space,
    joiner, word joiner, BOM, ...). Such text shows as nothing, so it counts as blank."""
    return all(ch.isspace() or unicodedata.category(ch) == "Cf" for ch in value)


def _strip(value):
    if not isinstance(value, str):
        return value
    # Only the blank check changes: non-blank text keeps its inner format characters (a ZWJ in an emoji
    # sequence, a ZWNJ in Persian), only the usual whitespace at the ends is removed.
    return "" if _invisible(value) else value.strip()


# One line of text (names, titles, emails): no control characters at all.
SafeLine = Annotated[str, AfterValidator(_check(LINE_BAD, "Remove control characters."))]
# Multi-line text: tabs and newlines are fine.
SafeText = Annotated[str, AfterValidator(_check(_TEXT_BAD, "Remove control characters."))]
# A SafeLine stripped *before* length checks, so a blank value fails min_length.
StrippedLine = Annotated[str, BeforeValidator(_strip), AfterValidator(_check(LINE_BAD, "Remove control characters."))]


def _not_invisible(value: str) -> str:
    if value and _invisible(value):
        raise ValueError("Write something other than blank space.")
    return value


# Note bodies: empty is allowed (a title-only note), but a body of only whitespace and invisible characters
# is refused, like an empty title is. Real text keeps its characters untouched.
NoteBody = Annotated[str, AfterValidator(_check(_TEXT_BAD, "Remove control characters.")), AfterValidator(_not_invisible)]
