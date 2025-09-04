from __future__ import annotations
import xml.etree.ElementTree as ET
from dfe.types import ParseOut
from dfe.base import collect_ns
from dfe.utils import text_or_none, only_digits, norm_dt

def parse_evento(root: ET.Element) -> ParseOut:
    ns = {"nfe": collect_ns(root)["nfe"]}
    ch   = text_or_none(root.find(".//nfe:chNFe", ns))
    tpe  = text_or_none(root.find(".//nfe:tpEvento", ns))
    desc = text_or_none(root.find(".//nfe:detEvento/nfe:descEvento", ns))
    seq  = text_or_none(root.find(".//nfe:nSeqEvento", ns))
    cnpj = only_digits(text_or_none(root.find(".//nfe:CNPJ", ns)))
    cpf  = only_digits(text_or_none(root.find(".//nfe:CPF", ns)))
    dh   = text_or_none(root.find(".//nfe:dhEvento", ns))
    prot = text_or_none(root.find(".//nfe:nProt", ns))

    out = ParseOut(
        tipo_documento="Evento",
        isevent="1",
        chave_acesso=ch,
        tipo_evento=tpe or desc,
        descricao_evento=desc or tpe,
        sequencia_evento=seq,
        cnpj_emitente=cnpj or None,
        cpf_emitente=cpf or None,
        data_evento=norm_dt(dh) or None,
        protocolo=prot,
    )
    if cnpj:
        out.cnpj = cnpj
    return out
