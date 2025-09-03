# src/dfe/DocumentoFiscalParser.py
from __future__ import annotations

import base64
import logging
import re
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Optional
import xml.etree.ElementTree as ET

# ------------------------------------------------------------
# Logging enxuto (compatível com Lambda e execução local)
# ------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)


# ------------------------------------------------------------
# Namespaces canônicos e utilidades
# ------------------------------------------------------------
@lru_cache(maxsize=64)
def _ns_uri(local: str) -> str:
    mapping = {
        "nfe": "http://www.portalfiscal.inf.br/nfe",
        "cte": "http://www.portalfiscal.inf.br/cte",
        "mdfe": "http://www.portalfiscal.inf.br/mdfe",
        # NFS-e (ABRASF variantes)
        "nfse1": "http://www.abrasf.org.br/nfse.xsd",
        "nfse2": "http://nfse.abrasf.org.br",
        # Assinatura XMLDSIG (eventos etc.)
        "ds": "http://www.w3.org/2000/09/xmldsig#",
    }
    return mapping[local]


def _local_name(tag: str) -> str:
    return tag.split("}")[-1].lower() if "}" in tag else tag.lower()


def _text(el: Optional[ET.Element]) -> Optional[str]:
    return el.text.strip() if (el is not None and el.text) else None


def _only_digits(s: Optional[str]) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def _norm_dt(val: Optional[str]) -> Optional[str]:
    """
    Normaliza datas para 'YYYY-MM-DD HH:MM:SS'.
    Mantém compat com chamadas que fazem slice [:10] para obter só a data.
    """
    if not val:
        return None
    s = val.strip()
    try:
        # ISO completo (com timezone opcional)
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        # Somente data
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return datetime.fromisoformat(s).strftime("%Y-%m-%d %H:%M:%S")
        # AAAAMMDD
        m = re.match(r"^(\d{4})(\d{2})(\d{2})$", s)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)} 00:00:00"
    except Exception:
        pass
    # Formato estranho: retorna como veio (caller faz slice [:10])
    return s


# ------------------------------------------------------------
# Parser principal
# ------------------------------------------------------------
class DocumentoFiscalParser:
    """
    Parser unificado e tolerante para NFe / NFCe / CTe / MDFe / NFS-e / Eventos.

    ⚠️ Compatibilidade garantida com chamadas existentes:
      - Retorna SEMPRE dicionário com as chaves usadas pelo seu pipeline:
          * "tipo_documento"   -> 'NF-e' | 'CT-e' | 'MDF-e' | 'NFS-e' | 'Evento'
          * "chave_acesso"     -> string (quando identificável)
          * "cnpj_emitente"    -> somente dígitos (se disponível)
          * "cpf_emitente"     -> somente dígitos (se disponível)
          * "data_emissao"     -> 'YYYY-MM-DD HH:MM:SS' (ou original)
          * "isevent"          -> "1" (apenas para eventos)
          * "data_evento"      -> (eventos) 'YYYY-MM-DD HH:MM:SS'
          * "tipo_evento"      -> (eventos) código do evento (quando existir)
          * "sequencia_evento" -> (eventos)
        Além disso, adicionamos (sem quebrar nada):
          * "cnpj_destinatario" / "cpf_destinatario" / "destinatario" (alias)
          * "descricao_evento" (eventos)
          * "cnpj" (alias de compat do emitente)
    """

    BASE_NS = {
        "nfe": _ns_uri("nfe"),
        "cte": _ns_uri("cte"),
        "mdfe": _ns_uri("mdfe"),
        "nfse": _ns_uri("nfse1"),  # default ABRASF
        "ds": _ns_uri("ds"),
    }
    NFSE_VARIANTS = (_ns_uri("nfse1"), _ns_uri("nfse2"))

    # ---------------- API pública ----------------
    def parse_documento_fiscal_string(self, xml_string: str) -> Dict[str, Any]:
        root = ET.fromstring(xml_string)
        return self._parse_root(root)

    def parse_documento_fiscal_arquivo(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        with open(path, "r", encoding=encoding) as f:
            return self.parse_documento_fiscal_string(f.read())

    # ---------------- Núcleo ----------------
    def _parse_root(self, root: ET.Element) -> Dict[str, Any]:
        tag = _local_name(root.tag)
        tipo_map = {
            "nfeproc": "NF-e",
            "nfe": "NF-e",
            "cteproc": "CT-e",
            "cte": "CT-e",
            "mdfeproc": "MDF-e",
            "mdfe": "MDF-e",
            "comppnfse": "NFS-e",
            "compnfse": "NFS-e",
            "nfse": "NFS-e",
            "proceventonfe": "Evento",
            "proceventocte": "Evento",
            "proceventomdfe": "Evento",
            "eventoproc": "Evento",
            "evento": "Evento",
        }
        tipo = tipo_map.get(tag)

        ns_candidates = self._collect_namespaces(root)

        if tipo == "NF-e":
            return self._parse_nfe_like(root, "nfe", ns_candidates, "NF-e")
        if tipo == "CT-e":
            return self._parse_nfe_like(root, "cte", ns_candidates, "CT-e")
        if tipo == "MDF-e":
            return self._parse_nfe_like(root, "mdfe", ns_candidates, "MDF-e")
        if tipo == "Evento":
            return self._parse_evento(root, ns_candidates)

        # Tentativa de NFS-e (heurística)
        if tipo == "NFS-e" or self._looks_like_nfse(root, ns_candidates):
            return self._parse_nfse(root, ns_candidates)

        return {"erro": f"Tipo de documento não identificado (tag='{tag}')"}

    # ---------------- Parsers específicos ----------------
    def _parse_nfe_like(
        self,
        root: ET.Element,
        ns_key: str,
        ns_candidates: Dict[str, str],
        tipo_documento: str,
    ) -> Dict[str, Any]:
        ns = {ns_key: ns_candidates.get(ns_key, self.BASE_NS[ns_key])}
        inf_tag = {"nfe": "infNFe", "cte": "infCte", "mdfe": "infMDFe"}[ns_key]

        inf = root.find(f".//{ns_key}:{inf_tag}", ns) or root.find(f".//{inf_tag}")
        chave = None
        if inf is not None:
            _id = inf.attrib.get("Id")
            if _id:
                chave = re.sub(r"^(NFe|CTe|MDFe)", "", _id, flags=re.IGNORECASE)

        # Emitente
        emit = root.find(f".//{ns_key}:emit", ns) or root.find(".//emit")
        emit_cnpj = _only_digits(_text(emit.find(f"{ns_key}:CNPJ", ns) if emit is not None else None) or
                                 _text(emit.find("CNPJ") if emit is not None else None))
        emit_cpf = _only_digits(_text(emit.find(f"{ns_key}:CPF", ns) if emit is not None else None) or
                                _text(emit.find("CPF") if emit is not None else None))

        # Destinatário
        dest = root.find(f".//{ns_key}:dest", ns) or root.find(".//dest")
        dest_cnpj = _only_digits(_text(dest.find(f"{ns_key}:CNPJ", ns) if dest is not None else None) or
                                 _text(dest.find("CNPJ") if dest is not None else None))
        dest_cpf = _only_digits(_text(dest.find(f"{ns_key}:CPF", ns) if dest is not None else None) or
                                _text(dest.find("CPF") if dest is not None else None))

        # Datas
        ide = root.find(f".//{ns_key}:ide", ns) or root.find(".//ide")
        dhEmi = _text(ide.find(f"{ns_key}:dhEmi", ns) if ide is not None else None) or \
                _text(ide.find(f"{ns_key}:dEmi", ns) if ide is not None else None)
        data_emissao = _norm_dt(dhEmi)

        # protocolo em documentos *proc*
        prot_paths = {
            "nfe": ".//nfe:protNFe/nfe:infProt/nfe:nProt",
            "cte": ".//cte:protCTe/cte:infProt/cte:nProt",
            "mdfe": ".//mdfe:protMDFe/mdfe:infProt/mdfe:nProt",
        }
        prot_ns = {
            "nfe": {"nfe": ns.get("nfe", self.BASE_NS["nfe"])},
            "cte": {"cte": ns.get("cte", self.BASE_NS["cte"])},
            "mdfe": {"mdfe": ns.get("mdfe", self.BASE_NS["mdfe"])},
        }
        protocolo = _text(root.find(prot_paths.get(ns_key, ""), prot_ns.get(ns_key, {}))) if ns_key in prot_paths else None

        # Retorno compatível + novos campos de destinatário
        out = {
            "tipo_documento": tipo_documento,
            "chave_acesso": chave,
            "cnpj_emitente": emit_cnpj or None,
            "cpf_emitente": emit_cpf or None,
            "cnpj_destinatario": dest_cnpj or None,
            "cpf_destinatario": dest_cpf or None,
            "data_emissao": data_emissao or None,
            "protocolo": protocolo,
        }
        # Aliases de compatibilidade esperados pelo pipeline
        if emit_cnpj:
            out["cnpj"] = emit_cnpj
        dest_alias = dest_cnpj or dest_cpf
        if dest_alias:
            out["destinatario"] = dest_alias
        return out

    def _parse_evento(self, root: ET.Element, ns_candidates: Dict[str, str]) -> Dict[str, Any]:
        ns = {"nfe": ns_candidates.get("nfe", self.BASE_NS["nfe"])}
        ch = _text(root.find(".//nfe:chNFe", ns))
        tp_code = _text(root.find(".//nfe:tpEvento", ns))  # código numérico quando existir
        desc = _text(root.find(".//nfe:detEvento/nfe:descEvento", ns))
        seq = _text(root.find(".//nfe:nSeqEvento", ns))
        cnpj = _only_digits(_text(root.find(".//nfe:CNPJ", ns)))
        cpf = _only_digits(_text(root.find(".//nfe:CPF", ns)))
        dh = _text(root.find(".//nfe:dhEvento", ns))
        prot = _text(root.find(".//nfe:nProt", ns))

        out = {
            "tipo_documento": "Evento",
            "isevent": "1",
            "chave_acesso": ch,
            "tipo_evento": tp_code or desc,       # mantém compat: devolve algo útil mesmo sem tpEvento
            "descricao_evento": desc or tp_code,  # campo adicional
            "sequencia_evento": seq,
            "cnpj_emitente": cnpj or None,
            "cpf_emitente": cpf or None,
            "data_evento": _norm_dt(dh) or None,
            "protocolo": prot,
        }
        # Compat extra
        if cnpj:
            out["cnpj"] = cnpj
        return out

    def _parse_nfse(self, root: ET.Element, ns_candidates: Dict[str, str]) -> Dict[str, Any]:
        nfse_ns_uri = ns_candidates.get("nfse")
        if nfse_ns_uri is None or nfse_ns_uri not in self.NFSE_VARIANTS:
            nfse_ns_uri = self.NFSE_VARIANTS[0]
        ns = {"nfse": nfse_ns_uri}

        # Nó base (varia entre prefeituras)
        inf = root.find(".//nfse:InfNfse", ns) or root.find(".//nfse:InfNFSe", ns) or root.find(".//nfse:infNfse", ns)

        numero = _text(root.find(".//nfse:IdentificacaoNfse/nfse:Numero", ns))
        if not numero and inf is not None:
            numero = _text(inf.find("nfse:Numero", ns))

        data_emissao = _text(root.find(".//nfse:DataEmissao", ns))
        if not data_emissao and inf is not None:
            data_emissao = _text(inf.find("nfse:DataEmissao", ns))

        # Prestador (emitente)
        emit = (
            _text(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:Cnpj", ns))
            or _text(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:CpfCnpj/nfse:Cnpj", ns))
            or _text(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:CpfCnpj/nfse:Cpf", ns))
        )
        emit = _only_digits(emit)

        # Tomador (destinatário)
        tom = (
            _text(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cnpj", ns)) or
            _text(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cpf", ns)) or
            _text(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:Cnpj", ns)) or
            _text(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:Cpf", ns))
        )
        dest_cnpjcpf = _only_digits(tom)

        out = {
            "tipo_documento": "NFS-e",
            "chave_acesso": numero,
            "cnpj_emitente": emit or None,
            "data_emissao": _norm_dt(data_emissao) or None,
            "protocolo": numero,  # muitas usam o mesmo número como protocolo
            "cnpj_destinatario": dest_cnpjcpf if (dest_cnpjcpf and len(dest_cnpjcpf) == 14) else None,
            "cpf_destinatario": dest_cnpjcpf if (dest_cnpjcpf and len(dest_cnpjcpf) == 11) else None,
        }
        if emit:
            out["cnpj"] = emit  # compat
        if dest_cnpjcpf:
            out["destinatario"] = dest_cnpjcpf  # alias compat
        return out

    # ---------------- Heurísticas e coleta de namespaces ----------------
    def _looks_like_nfse(self, root: ET.Element, ns_candidates: Dict[str, str]) -> bool:
        tag = _local_name(root.tag)
        if tag in {"compnfse", "comppnfse", "nfse"}:
            return True
        ns = {"nfse": ns_candidates.get("nfse", self.BASE_NS["nfse"])}
        return any(
            root.find(xpath, ns) is not None
            for xpath in (".//nfse:PrestadorServico", ".//nfse:TomadorServico", ".//nfse:InfNfse")
        )

    def _collect_namespaces(self, root: ET.Element) -> Dict[str, str]:
        ns = dict(self.BASE_NS)
        to_scan = [root] + list(root)[:10]
        for el in to_scan:
            if "}" in el.tag:
                uri = el.tag.split("}")[0].strip("{")
                if uri in self.NFSE_VARIANTS:
                    ns["nfse"] = uri
                elif uri == self.BASE_NS["nfe"]:
                    ns["nfe"] = uri
                elif uri == self.BASE_NS["cte"]:
                    ns["cte"] = uri
                elif uri == self.BASE_NS["mdfe"]:
                    ns["mdfe"] = uri
        return ns
