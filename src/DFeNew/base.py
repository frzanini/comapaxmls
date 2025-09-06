from __future__ import annotations
from typing import Dict
import xml.etree.ElementTree as ET
from DFeNew.logger import get_logger
from DFeNew.utils import ns_uri

logger = get_logger(__name__)

BASE_NS = {
    "nfe":  ns_uri("nfe"),
    "cte":  ns_uri("cte"),
    "mdfe": ns_uri("mdfe"),
    "nfse": ns_uri("nfse1"),  # default
    "ds":   ns_uri("ds"),
}
NFSE_VARIANTS = (ns_uri("nfse1"), ns_uri("nfse2"))

def collect_ns(root: ET.Element) -> Dict[str, str]:
    ns = dict(BASE_NS)
    to_scan = [root] + list(root)[:10]
    for el in to_scan:
        if "}" in el.tag:
            uri = el.tag.split("}")[0].strip("{")
            if uri in NFSE_VARIANTS: ns["nfse"] = uri
            elif uri == BASE_NS["nfe"]: ns["nfe"] = uri
            elif uri == BASE_NS["cte"]: ns["cte"] = uri
            elif uri == BASE_NS["mdfe"]: ns["mdfe"] = uri
    return ns
