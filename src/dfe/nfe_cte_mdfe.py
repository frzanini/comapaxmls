from __future__ import annotations
import re, xml.etree.ElementTree as ET
from dfe.types import ParseOut
from dfe.base import collect_ns
from dfe.utils import text_or_none, only_digits, norm_dt

def parse_nfe_cte_mdfe(root: ET.Element, tipo: str) -> ParseOut:
    ns = collect_ns(root)
    ns_key = {"NF-e":"nfe", "CT-e":"cte", "MDF-e":"mdfe"}[tipo]
    inf_tag = {"nfe":"infNFe", "cte":"infCte", "mdfe":"infMDFe"}[ns_key]

    inf = root.find(f".//{ns_key}:{inf_tag}", ns) or root.find(f".//{inf_tag}")
    chave = None
    if inf is not None:
        _id = inf.attrib.get("Id") or inf.attrib.get("id")
        if _id:
            chave = re.sub(r"^(NFe|CTe|MDFe)", "", _id, flags=re.IGNORECASE)

    emit = root.find(f".//{ns_key}:emit", ns) or root.find(".//emit")
    dest = root.find(f".//{ns_key}:dest", ns) or root.find(".//dest")

    emit_cnpj = only_digits(text_or_none(emit.find(f"{ns_key}:CNPJ", ns) if emit is not None else None)
                            or text_or_none(emit.find("CNPJ") if emit is not None else None))
    emit_cpf  = only_digits(text_or_none(emit.find(f"{ns_key}:CPF", ns) if emit is not None else None)
                            or text_or_none(emit.find("CPF") if emit is not None else None))

    dest_cnpj = only_digits(text_or_none(dest.find(f"{ns_key}:CNPJ", ns) if dest is not None else None)
                            or text_or_none(dest.find("CNPJ") if dest is not None else None))
    dest_cpf  = only_digits(text_or_none(dest.find(f"{ns_key}:CPF", ns) if dest is not None else None)
                            or text_or_none(dest.find("CPF") if dest is not None else None))

    ide = root.find(f".//{ns_key}:ide", ns) or root.find(".//ide")
    dhEmi = text_or_none(ide.find(f"{ns_key}:dhEmi", ns) if ide is not None else None) or \
            text_or_none(ide.find(f"{ns_key}:dEmi",  ns) if ide is not None else None)
    data_emissao = norm_dt(dhEmi)

    prot_paths = {
        "nfe":  ".//nfe:protNFe/nfe:infProt/nfe:nProt",
        "cte":  ".//cte:protCTe/cte:infProt/cte:nProt",
        "mdfe": ".//mdfe:protMDFe/mdfe:infProt/mdfe:nProt",
    }
    protocolo = text_or_none(root.find(prot_paths.get(ns_key, ""), {ns_key: ns[ns_key]})) if ns_key in prot_paths else None

    out = ParseOut(
        tipo_documento=tipo,
        chave_acesso=chave,
        cnpj_emitente=emit_cnpj or None,
        cpf_emitente=emit_cpf or None,
        cnpj_destinatario=dest_cnpj or None,
        cpf_destinatario=dest_cpf or None,
        data_emissao=data_emissao or None,
        protocolo=protocolo,
    )
    if emit_cnpj:
        out.cnpj = emit_cnpj
    dest_alias = dest_cnpj or dest_cpf
    if dest_alias:
        out.destinatario = dest_alias
    return out
