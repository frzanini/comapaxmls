from __future__ import annotations
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict
from dfe.base import collect_ns
from dfe.utils import text_or_none

_DEC = Decimal

@dataclass(frozen=True)
class NFeItem:
    cProd: Optional[str] = None
    xProd: Optional[str] = None
    NCM: Optional[str] = None
    CFOP: Optional[str] = None
    uCom: Optional[str] = None
    qCom: Optional[Decimal] = None
    vUnCom: Optional[Decimal] = None
    vProd: Optional[Decimal] = None
    CEST: Optional[str] = None
    CST: Optional[str] = None  # ou CSOSN
    EAN: Optional[str] = None

def _dec(v: Optional[str]) -> Optional[Decimal]:
    if not v:
        return None
    try:
        return _DEC(v).quantize(_DEC("0.0000"), rounding=ROUND_HALF_UP)
    except Exception:
        return None

class ItemsExtractor:
    """
    Extrai itens de DF-e. No momento: NFe (det/prod).
    Projetado para expandir para CTe/MDF-e/NFS-e, se houver itens relevantes.
    """
    def nfe_items(self, root: ET.Element) -> List[NFeItem]:
        ns: Dict[str, str] = collect_ns(root)
        items: List[NFeItem] = []
        for det in root.findall(".//nfe:det", ns) or []:
            prod = det.find("nfe:prod", ns)
            if prod is None:
                continue

            def _t(tag: str) -> Optional[str]:
                el = prod.find(f"nfe:{tag}", ns)
                return el.text.strip() if (el is not None and el.text) else None

            cProd = _t("cProd")
            xProd = _t("xProd")
            NCM   = _t("NCM")
            CFOP  = _t("CFOP")
            uCom  = _t("uCom")
            qCom  = _t("qCom")
            vUn   = _t("vUnCom")
            vProd = _t("vProd")
            CEST  = _t("CEST")
            EAN   = _t("cEAN") or _t("cEANTrib")

            CST = None
            imposto = det.find("nfe:imposto", ns)
            if imposto is not None:
                icms = imposto.find("nfe:ICMS", ns) or imposto.find(".//nfe:ICMS", ns)
                if icms is not None:
                    for ic in list(icms):
                        cst_el = ic.find("nfe:CST", ns) or ic.find("nfe:CSOSN", ns)
                        if cst_el is not None and cst_el.text:
                            CST = cst_el.text.strip()
                            break

            items.append(NFeItem(
                cProd=cProd, xProd=xProd, NCM=NCM, CFOP=CFOP, uCom=uCom,
                qCom=_dec(qCom), vUnCom=_dec(vUn), vProd=_dec(vProd),
                CEST=CEST, CST=CST, EAN=EAN,
            ))
        return items
