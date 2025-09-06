from __future__ import annotations
import re
from typing import Optional


_DIGITS = re.compile(r"\D+")


def only_digits(v: Optional[str]) -> str:
    return "" if not v else _DIGITS.sub("", v)