from __future__ import annotations
import json, logging
from datetime import datetime
from typing import Sequence, Optional
from .config import SiegConfig
from .types import XmlType
from .service import SiegIngestionService

log = logging.getLogger(__name__)

def _parse_types(seq: Optional[Sequence[str]])->Sequence[XmlType]:
    if not seq: return (XmlType.NFE, XmlType.CTE, XmlType.NFCE, XmlType.CFE, XmlType.MDFE)
    out = []
    for s in seq:
        try: out.append(XmlType[s.upper()])
        except KeyError: log.warning("Tipo XML inválido: %s", s)
    return tuple(out) or (XmlType.NFE,)

def lambda_handler(event, context):
    log.info("Evento: %s", json.dumps(event, ensure_ascii=False))
    svc = SiegIngestionService(SiegConfig.from_env())

    action = (event.get("action") or "intervalo_dias").lower().strip()
    participante = (event.get("participante") or "ambos")
    incluir_flip = bool(event.get("incluir_como_destinatario_quando_emitente", False))
    include_events = bool(event.get("include_events", False))
    xml_types = _parse_types(event.get("xml_types"))

    if action == "intervalo_dias":
        svc.baixar_intervalo_dias(days_back=int(event.get("days_back", 1)), xml_types=xml_types,
                                  include_events=include_events, cnpj=event.get("cnpj_cpf"),
                                  participante=participante, incluir_dest_quando_emitente=incluir_flip)
        return {"ok": True, "action": action}

    if action == "ano_mes":
        year, month = int(event["year"]), int(event["month"])
        cnpj = event.get("cnpj_cpf")
        if cnpj:
            svc.baixar_por_cnpj_ano_mes(cnpj=cnpj, year=year, month=month, incluir_eventos=include_events,
                                        xml_types=xml_types, participante=participante,
                                        incluir_dest_quando_emitente=incluir_flip)
        else:
            ini, fim = svc.month_range(year, month)
            svc.download_por_participante(start_date=ini, end_date=fim, xml_types=xml_types,
                                          include_events=include_events, cnpj=None,
                                          participante="ambos", incluir_dest_quando_emitente=False)
        return {"ok": True, "action": action}

    if action == "emissao":
        start = datetime.fromisoformat(event["start"].replace("Z","+00:00"))
        end   = datetime.fromisoformat(event["end"].replace("Z","+00:00"))
        svc.download_por_participante(start_date=start, end_date=end, xml_types=xml_types,
                                      include_events=include_events, cnpj=event.get("cnpj_cpf"),
                                      participante=participante, incluir_dest_quando_emitente=incluir_flip)
        return {"ok": True, "action": action}

    if action == "nfse":
        start = datetime.fromisoformat(event["start"].replace("Z","+00:00"))
        end   = datetime.fromisoformat(event["end"].replace("Z","+00:00"))
        svc.download_nfse_por_emissao(start_date=start, end_date=end,
            cnpj_emit=event.get("cnpj_cpf") if participante!="destinatario" else None,
            cnpj_dest=event.get("cnpj_cpf") if participante!="emitente" else None)
        return {"ok": True, "action": action}

    raise ValueError(f"Ação inválida: {action}")
