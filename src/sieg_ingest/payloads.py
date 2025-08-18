from __future__ import annotations
from datetime import datetime
from typing import Dict, Optional
from .types import XmlType, only_digits

class PayloadBuilder:
    @staticmethod
    def padrao(*, xml_type: XmlType, take: int, skip: int,
               start: datetime, end: datetime, include_events: bool,
               cnpj_emit: Optional[str], cnpj_dest: Optional[str]) -> Dict:
        p = {
            "XmlType": int(xml_type),
            "Take": int(take),
            "Skip": int(skip),
            "DataEmissaoInicio": start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            "DataEmissaoFim": end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            "Downloadevent": bool(include_events),
        }
        if cnpj_emit: p["CnpjEmit"] = only_digits(cnpj_emit)
        if cnpj_dest: p["CnpjDest"] = only_digits(cnpj_dest)
        return p

    @staticmethod
    def nfse(*, take: int, skip: int, start: datetime, end: datetime,
             cnpj_emit: Optional[str], cnpj_dest: Optional[str]) -> Dict:
        p = {
            "XmlType": int(XmlType.NFSE),
            "Take": int(take),
            "Skip": int(skip),
            "DataEmissaoInicio": start.strftime("%Y-%m-%d"),
            "DataEmissaoFim": end.strftime("%Y-%m-%d"),
        }
        if cnpj_emit: p["CnpjEmit"] = only_digits(cnpj_emit)
        if cnpj_dest: p["CnpjDest"] = only_digits(cnpj_dest)
        return p
