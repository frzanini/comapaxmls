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

# === PATCH: ADITIVOS PARA INTEGRAÇÃO COM sci_export ==========================
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple, Optional, Dict, Any

_DEC = Decimal  # atalho local

def _only_digits_local(s: Optional[str]) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())

def _ymd8_from_norm(norm_dt: Optional[str]) -> Optional[str]:
    """
    Converte 'YYYY-MM-DD HH:MM:SS' (ou 'YYYY-MM-DD') para 'YYYYMMDD'.
    """
    if not norm_dt:
        return None
    # norm_dt esperado do _norm_dt() já existente
    try:
        y, m, d = norm_dt[:10].split("-")
        return f"{y}{m}{d}"
    except Exception:
        return None

def _direction_for_cnpj(cnpj_alvo: Optional[str], cnpj_emit: Optional[str], cnpj_dest: Optional[str]) -> Optional[str]:
    """
    Determina a 'direção' da nota em relação ao CNPJ alvo:
      - 'saida'  se cnpj_emit == cnpj_alvo
      - 'entrada' se cnpj_dest == cnpj_alvo
      - None caso não haja match
    """
    if not cnpj_alvo:
        return None
    z_alvo = _only_digits_local(cnpj_alvo).zfill(14)
    if (cnpj_emit or "").zfill(14) == z_alvo:
        return "saida"
    if (cnpj_dest or "").zfill(14) == z_alvo:
        return "entrada"
    return None

@dataclass(frozen=True)
class NFeItemSCI:
    """
    Estrutura mínima para o Anexo 07 (Produtos),
    mantendo nomes próximos aos layouts SCI mais comuns.
    """
    cProd: Optional[str] = None
    xProd: Optional[str] = None
    NCM: Optional[str] = None
    CFOP: Optional[str] = None
    uCom: Optional[str] = None
    qCom: Optional[Decimal] = None
    vUnCom: Optional[Decimal] = None
    vProd: Optional[Decimal] = None
    CEST: Optional[str] = None
    CST: Optional[str] = None     # ou CSOSN
    EAN: Optional[str] = None

@dataclass(frozen=True)
class NFeHeaderSCI:
    """
    Cabeçalho mínimo para Anexos 04/09 e metadados.
    """
    chave_acesso: Optional[str]
    cnpj_emitente: Optional[str]
    cnpj_destinatario: Optional[str]
    data_emissao_ymd: Optional[str]      # AAAAMMDD
    data_entrada_ymd: Optional[str]      # AAAAMMDD
    protocolo: Optional[str]
    modelo: Optional[str]
    serie: Optional[str]
    numero: Optional[str]
    tipo_documento: str                   # "NF-e", "CT-e"...

@dataclass(frozen=True)
class NFeSCI:
    header: NFeHeaderSCI
    itens: List[NFeItemSCI]

class DocumentoFiscalSCIAdapter:
    """
    Adapter que expõe dados prontos para os Anexos do SCI
    a partir do DocumentoFiscalParser (somente NF-e aqui).
    """

    def __init__(self) -> None:
        self._parser = DocumentoFiscalParser()

    def parse_nfe_with_items(self, xml_text: str) -> Optional[NFeSCI]:
        """
        Retorna uma estrutura com header + itens para NF-e.
        Caso o XML não seja NF-e válida, retorna None.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return None

        ns = self._parser._collect_namespaces(root)
        # Heurística simples: se não achar elementos básicos de NFe, aborta
        ide = root.find(f".//nfe:ide", ns)
        emit = root.find(f".//nfe:emit", ns)
        if ide is None or emit is None:
            return None

        # ---- Cabeçalho (reuso da lógica já existente no parser base) ----
        head_dict = self._parser.parse_documento_fiscal(xml_text)  # NÃO remove nada existente

        if not head_dict or head_dict.get("tipo_documento") != "NF-e":
            return None

        # Chaves esperadas
        chave = head_dict.get("chave_acesso")
        cnpj_emit = _only_digits_local(head_dict.get("cnpj_emitente"))
        cnpj_dest = _only_digits_local(head_dict.get("cnpj_destinatario"))
        data_emissao_norm = head_dict.get("data_emissao")  # 'YYYY-MM-DD HH:MM:SS'
        data_emissao_ymd = _ymd8_from_norm(data_emissao_norm)

        # Algumas NFe trazem data de entrada (dEntrega) – nem sempre presente
        d_entrada = None
        d1 = root.find(".//nfe:ide/nfe:dSaiEnt", ns)
        if d1 is not None and d1.text:
            d_entrada = self._parser._norm_dt(d1.text)
        data_entrada_ymd = _ymd8_from_norm(d_entrada)

        # Modelo/Série/Número
        mod = (ide.find("nfe:mod", ns).text if ide is not None and ide.find("nfe:mod", ns) is not None else None)
        serie = (ide.find("nfe:serie", ns).text if ide is not None and ide.find("nfe:serie", ns) is not None else None)
        nNF = (ide.find("nfe:nNF", ns).text if ide is not None and ide.find("nfe:nNF", ns) is not None else None)

        header = NFeHeaderSCI(
            chave_acesso=chave,
            cnpj_emitente=cnpj_emit or None,
            cnpj_destinatario=cnpj_dest or None,
            data_emissao_ymd=data_emissao_ymd,
            data_entrada_ymd=data_entrada_ymd,
            protocolo=head_dict.get("protocolo"),
            modelo=mod,
            serie=serie,
            numero=nNF,
            tipo_documento="NF-e",
        )

        # ---- Itens (det/prod) ----
        itens: List[NFeItemSCI] = []
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

            # Trib (CST/CSOSN)
            CST = None
            imposto = det.find("nfe:imposto", ns)
            if imposto is not None:
                icms = (
                    imposto.find("nfe:ICMS", ns)
                    or imposto.find(".//nfe:ICMS", ns)
                )
                if icms is not None:
                    # nós podem ser ICMS00/ICMSSN102/etc. – pegue o primeiro filho
                    for ic in list(icms):
                        cst_el = ic.find("nfe:CST", ns) or ic.find("nfe:CSOSN", ns)
                        if cst_el is not None and cst_el.text:
                            CST = cst_el.text.strip()
                            break

            def _d(v: Optional[str]) -> Optional[Decimal]:
                if not v:
                    return None
                try:
                    return _DEC(v).quantize(_DEC("0.0000"), rounding=ROUND_HALF_UP)
                except Exception:
                    return None

            item = NFeItemSCI(
                cProd=cProd, xProd=xProd, NCM=NCM, CFOP=CFOP, uCom=uCom,
                qCom=_d(qCom), vUnCom=_d(vUn), vProd=_d(vProd), CEST=CEST,
                CST=CST, EAN=EAN,
            )
            itens.append(item)

        return NFeSCI(header=header, itens=itens)

    # --------- Auxiliares públicos para o sci_export -------------------
    def nota_matches_date(self, nfe: NFeSCI, ano: Optional[int], mes: Optional[int], dia: Optional[int]) -> bool:
        """
        Aplica filtro por data usando data_entrada (quando existir), caso contrário data_emissao.
        """
        ymd = nfe.header.data_entrada_ymd or nfe.header.data_emissao_ymd
        if not ymd or len(ymd) != 8:
            return False if (ano or mes or dia) else True  # sem datas, só passa se não pediu filtro
        y, m, d = int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8])
        if ano is not None and y != ano:
            return False
        if mes is not None and m != mes:
            return False
        if dia is not None and d != dia:
            return False
        return True

    def direction(self, nfe: NFeSCI, cnpj_alvo: Optional[str]) -> Optional[str]:
        return _direction_for_cnpj(cnpj_alvo, nfe.header.cnpj_emitente, nfe.header.cnpj_destinatario)
# === /PATCH ==================================================================

    # === ADITIVO: API de alto nível para o sci_export ===
    def parse_documento_fiscal(self, xml_text: str):
        """
        Extrai um dicionário padronizado com campos mínimos para integração com o sci_export.
        Suporta (neste aditivo) NF-e. Mantém compatibilidade: não remove nada existente.

        Retorna:
            dict | None com chaves:
              - tipo_documento: "NF-e"
              - chave_acesso: str | None
              - cnpj_emitente: str | None  (somente dígitos, 14 se CNPJ)
              - cnpj_destinatario: str | None
              - data_emissao: str | None   ("YYYY-MM-DD HH:MM:SS")
              - protocolo: str | None
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return None

        ns = self._collect_namespaces(root)

        # Heurística: NF-e tem ide/emit/dest em namespace da NFe
        ide = root.find(".//nfe:ide", ns) or root.find(".//NFe/infNFe/ide")
        emit = root.find(".//nfe:emit", ns) or root.find(".//NFe/infNFe/emit")
        dest = root.find(".//nfe:dest", ns) or root.find(".//NFe/infNFe/dest")

        if ide is None or emit is None:
            # Não sendo NF-e (para este aditivo), devolve None
            return None

        # ---- tipo_documento
        tipo_documento = "NF-e"

        # ---- chave de acesso
        # 1) tenta @Id do infNFe (ex: "NFe351..."), 2) fallback para protNFe
        chave = None
        infnfe = root.find(".//nfe:infNFe", ns) or root.find(".//NFe/infNFe")
        if infnfe is not None:
            chave = infnfe.get("Id") or infnfe.get("id")
            if chave:
                chave = chave.replace("NFe", "").strip()
        if not chave:
            # protNFe → infProt/chNFe
            ch = root.find(".//nfe:protNFe/nfe:infProt/nfe:chNFe", ns)
            if ch is not None and ch.text:
                chave = ch.text.strip()

        # ---- CNPJ/CPF emitente
        def _text(el):
            return el.text.strip() if (el is not None and el.text) else None

        def _only_digits(s):
            return "".join(ch for ch in (s or "") if ch.isdigit())

        cnpj_emit = None
        if emit is not None:
            cnpj_emit = _text(emit.find("nfe:CNPJ", ns)) or _text(emit.find("CNPJ"))
            cpf_emit = _text(emit.find("nfe:CPF", ns)) or _text(emit.find("CPF"))
            cnpj_emit = _only_digits(cnpj_emit or cpf_emit)

        # ---- CNPJ/CPF destinatário
        cnpj_dest = None
        if dest is not None:
            cnpj_dest = _text(dest.find("nfe:CNPJ", ns)) or _text(dest.find("CNPJ"))
            cpf_dest = _text(dest.find("nfe:CPF", ns)) or _text(dest.find("CPF"))
            cnpj_dest = _only_digits(cnpj_dest or cpf_dest)

        # ---- Datas
        # Preferencialmente dhEmi; se não houver, usa dEmi; normaliza via _norm_dt já existente
        data_emissao_norm = None
        dhEmi = ide.find("nfe:dhEmi", ns) if ide is not None else None
        dEmi = ide.find("nfe:dEmi", ns) if ide is not None else None
        if dhEmi is not None and dhEmi.text:
            data_emissao_norm = self._norm_dt(dhEmi.text)
        elif dEmi is not None and dEmi.text:
            data_emissao_norm = self._norm_dt(dEmi.text)

        # ---- Protocolo (se existir)
        protocolo = None
        nProt = root.find(".//nfe:protNFe/nfe:infProt/nfe:nProt", ns)
        if nProt is not None and nProt.text:
            protocolo = nProt.text.strip()

        return {
            "tipo_documento": tipo_documento,
            "chave_acesso": chave,
            "cnpj_emitente": cnpj_emit or None,
            "cnpj_destinatario": cnpj_dest or None,
            "data_emissao": data_emissao_norm,   # "YYYY-MM-DD HH:MM:SS"
            "protocolo": protocolo,
        }
