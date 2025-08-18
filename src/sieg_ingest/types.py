import re
from enum import IntEnum
from typing import Optional

class XmlType(IntEnum):
    NFE = 1
    CTE = 2
    NFCE = 3
    CFE = 4
    MDFE = 5
    NFSE = 6

_ONLY_DIGITS = re.compile(r"\D+")
def only_digits(v: Optional[str]) -> Optional[str]:
    return _ONLY_DIGITS.sub("", v) if v else v
