from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ParseOut(BaseModel):
    # contrato compatível com sua classe atual
    tipo_documento: Optional[str] = None
    chave_acesso: Optional[str] = None
    cnpj_emitente: Optional[str] = None
    cpf_emitente: Optional[str] = None
    cnpj_destinatario: Optional[str] = None
    cpf_destinatario: Optional[str] = None
    data_emissao: Optional[str] = None
    protocolo: Optional[str] = None
    # eventos
    isevent: Optional[str] = None
    data_evento: Optional[str] = None
    tipo_evento: Optional[str] = None
    sequencia_evento: Optional[str] = None
    descricao_evento: Optional[str] = None
    # aliases compat
    cnpj: Optional[str] = None
    destinatario: Optional[str] = None

    def asdict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)
