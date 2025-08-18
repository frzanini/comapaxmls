from __future__ import annotations
import base64, logging
from typing import Optional, Tuple
from dfe.DocumentoFiscalParser import DocumentoFiscalParser

log = logging.getLogger(__name__)

class XmlParserAdapter:
    def __init__(self) -> None:
        self.parser = DocumentoFiscalParser()

    def parse_item_b64(self, item_b64: str) -> Optional[Tuple[str,str,str,str]]:
        # -> (xml_text, cnpj_emit, data_yyyy_mm_dd, file_name)
        try:
            xml_text = base64.b64decode(item_b64).decode("utf-8")
        except Exception as e:
            log.warning("Base64 inválido: %s", e); return None

        r = self.parser.parse_documento_fiscal_string(xml_text)
        if not isinstance(r, dict) or "erro" in r: return None

        chave = r.get("chave_acesso")
        cnpj_emit = r.get("cnpj_emitente") or r.get("cnpj") or r.get("cpf_emitente")
        data = (r.get("data_evento") if r.get("isevent")=="1" else r.get("data_emissao")) or ""
        data = data[:10] if len(data)>=10 else None
        if not (chave and cnpj_emit and data): return None

        if r.get("isevent")=="1":
            fname = f"{chave}_{r.get('tipo_documento')}_{r.get('tipo_evento')}_{r.get('sequencia_evento')}.xml"
        else:
            fname = f"{chave}_{r.get('tipo_documento')}.xml"
        return xml_text, cnpj_emit, data, fname
