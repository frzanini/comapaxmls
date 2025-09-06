from __future__ import annotations
import xml.etree.ElementTree as ET
from DFeNew.types import ParseOut
from DFeNew.base import collect_ns, NFSE_VARIANTS
from DFeNew.utils import text_or_none, only_digits, norm_dt

def looks_like_nfse(root: ET.Element) -> bool:
    tag = root.tag.split("}")[-1].lower() if "}" in root.tag else root.tag.lower()
    if tag in {"compnfse", "comppnfse", "nfse"}:
        return True
    ns = {"nfse": collect_ns(root).get("nfse")}
    return any(root.find(x, ns) is not None for x in (".//nfse:PrestadorServico", ".//nfse:TomadorServico", ".//nfse:InfNfse"))

def parse_nfse(root: ET.Element) -> ParseOut:
    ns = collect_ns(root)
    nfse_ns_uri = ns.get("nfse")
    if nfse_ns_uri is None or nfse_ns_uri not in NFSE_VARIANTS:
        nfse_ns_uri = NFSE_VARIANTS[0]
    ns = {"nfse": nfse_ns_uri}

    inf = root.find(".//nfse:InfNfse", ns) or root.find(".//nfse:InfNFSe", ns) or root.find(".//nfse:infNfse", ns)

    numero = text_or_none(root.find(".//nfse:IdentificacaoNfse/nfse:Numero", ns))
    if not numero and inf is not None:
        numero = text_or_none(inf.find("nfse:Numero", ns))

    data_emissao = text_or_none(root.find(".//nfse:DataEmissao", ns)) or (text_or_none(inf.find("nfse:DataEmissao", ns)) if inf is not None else None)

    emit = (
        text_or_none(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:Cnpj", ns))
        or text_or_none(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:CpfCnpj/nfse:Cnpj", ns))
        or text_or_none(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:CpfCnpj/nfse:Cpf", ns))
    )
    emit = only_digits(emit)

    tom = (
        text_or_none(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cnpj", ns)) or
        text_or_none(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cpf", ns)) or
        text_or_none(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:Cnpj", ns)) or
        text_or_none(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:Cpf", ns))
    )
    dest = only_digits(tom)

    out = ParseOut(
        tipo_documento="NFS-e",
        chave_acesso=numero,
        cnpj_emitente=emit or None,
        data_emissao=norm_dt(data_emissao) or None,
        protocolo=numero,
        cnpj_destinatario=dest if (dest and len(dest) == 14) else None,
        cpf_destinatario=dest if (dest and len(dest) == 11) else None,
    )
    if emit:
        out.cnpj = emit
    if dest:
        out.destinatario = dest
    return out
