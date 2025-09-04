from __future__ import annotations
import re, xml.etree.ElementTree as ET
from typing import Optional, Dict
from dfe.base import collect_ns
from dfe.utils import text_or_none, only_digits, norm_dt

class HeaderExtractor:
    """
    Extrai metadados comuns de DF-e (NFe/CTe/MDF-e/NFS-e/Eventos)
    sem amarrar ao formato de retorno – para reuso interno.
    """

    def _chave_from_inftag(self, root: ET.Element, ns: Dict[str, str], ns_key: str, inf_tag: str) -> Optional[str]:
        inf = root.find(f".//{ns_key}:{inf_tag}", ns) or root.find(f".//{inf_tag}")
        if inf is None:
            return None
        _id = inf.attrib.get("Id") or inf.attrib.get("id")
        if not _id:
            return None
        return re.sub(r"^(NFe|CTe|MDFe)", "", _id, flags=re.IGNORECASE)

    def nfe(self, root: ET.Element) -> Dict[str, Optional[str]]:
        ns = collect_ns(root)
        ns_key = "nfe"
        ide = root.find(f".//{ns_key}:ide", ns) or root.find(".//ide")
        emit = root.find(f".//{ns_key}:emit", ns) or root.find(".//emit")
        dest = root.find(f".//{ns_key}:dest", ns) or root.find(".//dest")
        out = {
            "chave_acesso": self._chave_from_inftag(root, ns, ns_key, "infNFe"),
            "cnpj_emitente": only_digits(text_or_none(emit.find(f"{ns_key}:CNPJ", ns) if emit is not None else None) or text_or_none(emit.find("CNPJ") if emit is not None else None)) or None,
            "cpf_emitente":  only_digits(text_or_none(emit.find(f"{ns_key}:CPF", ns)  if emit is not None else None) or text_or_none(emit.find("CPF")  if emit is not None else None)) or None,
            "cnpj_destinatario": only_digits(text_or_none(dest.find(f"{ns_key}:CNPJ", ns) if dest is not None else None) or text_or_none(dest.find("CNPJ") if dest is not None else None)) or None,
            "cpf_destinatario":  only_digits(text_or_none(dest.find(f"{ns_key}:CPF", ns)  if dest is not None else None) or text_or_none(dest.find("CPF")  if dest is not None else None)) or None,
            "data_emissao": norm_dt(text_or_none(ide.find(f"{ns_key}:dhEmi", ns) if ide is not None else None) or text_or_none(ide.find(f"{ns_key}:dEmi", ns) if ide is not None else None)) or None,
            "protocolo": text_or_none(root.find(".//nfe:protNFe/nfe:infProt/nfe:nProt", {"nfe": ns["nfe"]})),
        }
        return out

    def cte(self, root: ET.Element) -> Dict[str, Optional[str]]:
        ns = collect_ns(root); ns_key = "cte"
        ide = root.find(f".//{ns_key}:ide", ns) or root.find(".//ide")
        emit = root.find(f".//{ns_key}:emit", ns) or root.find(".//emit")
        dest = root.find(f".//{ns_key}:dest", ns) or root.find(".//dest")
        return {
            "chave_acesso": self._chave_from_inftag(root, ns, ns_key, "infCte"),
            "cnpj_emitente": only_digits(text_or_none(emit.find(f"{ns_key}:CNPJ", ns) if emit is not None else None) or text_or_none(emit.find("CNPJ") if emit is not None else None)) or None,
            "cpf_emitente":  only_digits(text_or_none(emit.find(f"{ns_key}:CPF", ns)  if emit is not None else None) or text_or_none(emit.find("CPF")  if emit is not None else None)) or None,
            "cnpj_destinatario": only_digits(text_or_none(dest.find(f"{ns_key}:CNPJ", ns) if dest is not None else None) or text_or_none(dest.find("CNPJ") if dest is not None else None)) or None,
            "cpf_destinatario":  only_digits(text_or_none(dest.find(f"{ns_key}:CPF", ns)  if dest is not None else None) or text_or_none(dest.find("CPF")  if dest is not None else None)) or None,
            "data_emissao": norm_dt(text_or_none(ide.find(f"{ns_key}:dhEmi", ns) if ide is not None else None)) or None,
            "protocolo": text_or_none(root.find(".//cte:protCTe/cte:infProt/cte:nProt", {"cte": ns["cte"]})),
        }

    def mdfe(self, root: ET.Element) -> Dict[str, Optional[str]]:
        ns = collect_ns(root); ns_key = "mdfe"
        ide = root.find(f".//{ns_key}:ide", ns) or root.find(".//ide")
        emit = root.find(f".//{ns_key}:emit", ns) or root.find(".//emit")
        return {
            "chave_acesso": self._chave_from_inftag(root, ns, ns_key, "infMDFe"),
            "cnpj_emitente": only_digits(text_or_none(emit.find(f"{ns_key}:CNPJ", ns) if emit is not None else None) or text_or_none(emit.find("CNPJ") if emit is not None else None)) or None,
            "cpf_emitente":  only_digits(text_or_none(emit.find(f"{ns_key}:CPF", ns)  if emit is not None else None) or text_or_none(emit.find("CPF")  if emit is not None else None)) or None,
            "data_emissao": norm_dt(text_or_none(ide.find(f"{ns_key}:dhEmi", ns) if ide is not None else None)) or None,
            "protocolo": text_or_none(root.find(".//mdfe:protMDFe/mdfe:infProt/mdfe:nProt", {"mdfe": ns["mdfe"]})),
        }

    def evento(self, root: ET.Element) -> Dict[str, Optional[str]]:
        ns = {"nfe": collect_ns(root)["nfe"]}
        return {
            "chave_acesso": text_or_none(root.find(".//nfe:chNFe", ns)),
            "tipo_evento": text_or_none(root.find(".//nfe:tpEvento", ns)),
            "descricao_evento": text_or_none(root.find(".//nfe:detEvento/nfe:descEvento", ns)),
            "sequencia_evento": text_or_none(root.find(".//nfe:nSeqEvento", ns)),
            "cnpj_emitente": only_digits(text_or_none(root.find(".//nfe:CNPJ", ns))) or None,
            "cpf_emitente":  only_digits(text_or_none(root.find(".//nfe:CPF", ns))) or None,
            "data_evento": norm_dt(text_or_none(root.find(".//nfe:dhEvento", ns))) or None,
            "protocolo": text_or_none(root.find(".//nfe:nProt", ns)),
        }

    def nfse(self, root: ET.Element) -> Dict[str, Optional[str]]:
        from dfe.nfse import looks_like_nfse
        ns = collect_ns(root)
        if not looks_like_nfse(root):
            return {}
        nf = {"nfse": ns["nfse"]}
        numero = text_or_none(root.find(".//nfse:IdentificacaoNfse/nfse:Numero", nf))
        data_emissao = text_or_none(root.find(".//nfse:DataEmissao", nf))
        emit = (
            text_or_none(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:Cnpj", nf))
            or text_or_none(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:CpfCnpj/nfse:Cnpj", nf))
            or text_or_none(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:CpfCnpj/nfse:Cpf", nf))
        )
        tom = (
            text_or_none(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cnpj", nf)) or
            text_or_none(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cpf", nf))
        )
        return {
            "chave_acesso": numero,
            "cnpj_emitente": only_digits(emit) or None,
            "data_emissao": norm_dt(data_emissao) or None,
            "protocolo": numero,
            "cnpj_destinatario": only_digits(tom) if (tom and len(only_digits(tom)) == 14) else None,
            "cpf_destinatario": only_digits(tom) if (tom and len(only_digits(tom)) == 11) else None,
        }
