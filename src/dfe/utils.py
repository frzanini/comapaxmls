from __future__ import annotations
import re
from datetime import datetime
from functools import lru_cache
from typing import Optional

def only_digits(s: Optional[str]) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())

def local_name(tag: str) -> str:
    return tag.split("}")[-1].lower() if "}" in tag else tag.lower()

def text_or_none(el) -> Optional[str]:
    return el.text.strip() if (el is not None and el.text) else None

def norm_dt(val: Optional[str]) -> Optional[str]:
    """Normaliza para 'YYYY-MM-DD HH:MM:SS'."""
    if not val:
        return None
    s = val.strip()
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return datetime.fromisoformat(s).strftime("%Y-%m-%d %H:%M:%S")
        m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)} 00:00:00"
    except Exception:
        pass
    return s

@lru_cache(maxsize=64)
def ns_uri(local: str) -> str:
    mapping = {
        "nfe":  "http://www.portalfiscal.inf.br/nfe",
        "cte":  "http://www.portalfiscal.inf.br/cte",
        "mdfe": "http://www.portalfiscal.inf.br/mdfe",
        "nfse1":"http://www.abrasf.org.br/nfse.xsd",
        "nfse2":"http://nfse.abrasf.org.br",
        "ds":   "http://www.w3.org/2000/09/xmldsig#",
    }
    return mapping[local]
