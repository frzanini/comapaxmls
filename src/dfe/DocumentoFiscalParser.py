"""
DocumentoFiscalParser – otimizado p/ AWS Lambda
- Foco em performance, baixo overhead de logging, e detecção robusta de NFSe (ABRASF variantes)
- Pode ser usado em execução local ou invocado por Lambda via `lambda_handler`

Requisitos do runtime Lambda: Python 3.11 (boto3 já disponível no ambiente AWS)
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Optional

try:
    # stdlib – mais leve que libs externas
    import xml.etree.ElementTree as ET
except Exception as e:  # pragma: no cover
    raise RuntimeError("xml.etree.ElementTree indisponível") from e

# Boto3 é nativo no runtime AWS Lambda
try:  # import tardio – só quando necessário (S3)
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None  # evita import se não for usar S3


# --------------------------- Logging ---------------------------
logger = logging.getLogger(__name__)
# Em Lambda, NÃO chame basicConfig repetidamente. Respeite o handler global.
if not logger.handlers:
    logger.setLevel(logging.INFO)


# --------------------------- Helpers ---------------------------
@lru_cache(maxsize=64)
def _ns_uri(local: str) -> str:
    """URIs oficiais dos DF-e mais frequentes."""
    mapping = {
        "nfe": "http://www.portalfiscal.inf.br/nfe",
        "cte": "http://www.portalfiscal.inf.br/cte",
        "mdfe": "http://www.portalfiscal.inf.br/mdfe",
        # NFS-e (múltiplos layouts ABRASF)
        "nfse1": "http://www.abrasf.org.br/nfse.xsd",
        "nfse2": "http://nfse.abrasf.org.br",
        # Assinatura
        "ds": "http://www.w3.org/2000/09/xmldsig#",
    }
    return mapping[local]


def _local_name(tag: str) -> str:
    return tag.split("}")[-1].lower() if "}" in tag else tag.lower()


def _text(el: Optional[ET.Element]) -> Optional[str]:
    return el.text.strip() if el is not None and el.text else None


class DocumentoFiscalParser:
    """Parser performático e tolerante a variações de schema para NFe/CTe/MDFe/NFSe."""

    # namespaces base (usados como fallback)
    BASE_NS = {
        "nfe": _ns_uri("nfe"),
        "cte": _ns_uri("cte"),
        "mdfe": _ns_uri("mdfe"),
        "nfse": _ns_uri("nfse1"),  # default ABRASF
        "ds": _ns_uri("ds"),
    }

    # variantes de NFSe (ABRASF) – muitas prefeituras mudam o namespace
    NFSE_VARIANTS = (
        _ns_uri("nfse1"),
        _ns_uri("nfse2"),
    )

    # --------------------------- API pública ---------------------------
    def parse_documento_fiscal_string(self, xml_string: str) -> Dict[str, Any]:
        root = ET.fromstring(xml_string)
        return self._parse_root(root)

    def parse_documento_fiscal_arquivo(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        with open(path, "r", encoding=encoding) as f:
            return self.parse_documento_fiscal_string(f.read())

    # --------------------------- Lambda Handler ---------------------------
    def lambda_handler(self, event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
        """Permite invocação direta em Lambda.

        Eventos aceitos:
        - {"xml": "<xml...>"} (string XML) ou {"xml_base64": "..."}
        - {"s3_bucket": "...", "s3_key": "..."}
        Retorna JSON com o dicionário do documento (ou erro).
        """
        try:
            if "xml" in event:
                xml_str = event["xml"]
            elif "xml_base64" in event:
                xml_str = base64.b64decode(event["xml_base64"]).decode("utf-8", "ignore")
            elif "s3_bucket" in event and "s3_key" in event:
                if boto3 is None:
                    raise RuntimeError("boto3 não disponível no ambiente")
                s3 = boto3.client("s3")
                obj = s3.get_object(Bucket=event["s3_bucket"], Key=event["s3_key"])  # type: ignore
                body = obj["Body"].read()
                xml_str = body.decode("utf-8", "ignore")
            else:
                return {"erro": "Evento inválido. Informe 'xml'|'xml_base64' ou 's3_bucket'+'s3_key'"}

            result = self.parse_documento_fiscal_string(xml_str)
            return result
        except Exception as e:  # log enxuto
            logger.exception("Falha no lambda_handler")
            return {"erro": str(e)}


    # --------------------------- Núcleo ---------------------------
    def _parse_root(self, root: ET.Element) -> Dict[str, Any]:
        tag = _local_name(root.tag)

        # Normalização: algumas vezes o root é *proc*, noutras a própria nota
        # Mapeia tags finais para tipos
        tipo_mapping = {
            "nfeproc": "NF-e",
            "nfe": "NF-e",
            "cteproc": "CT-e",
            "cte": "CT-e",
            "mdfeproc": "MDF-e",
            "mdfe": "MDF-e",
            "comppnfse": "NFS-e",  # variações comuns (ex.: CompNfse/CompNFSe)
            "compnfse": "NFS-e",
            "nfse": "NFS-e",
            "proceventonfe": "Evento",
            "proceventocte": "Evento",
            "proceventomdfe": "Evento",
            "eventoproc": "Evento",
            "evento": "Evento",
        }
        tipo = tipo_mapping.get(tag)

        # Descoberta de namespaces do documento (mais barato que tentar nsmap)
        ns_candidates = self._collect_namespaces(root)

        if tipo == "NF-e":
            return self._parse_nfe_like(root, "nfe", ns_candidates, tipo)
        if tipo == "CT-e":
            return self._parse_nfe_like(root, "cte", ns_candidates, tipo)
        if tipo == "MDF-e":
            return self._parse_nfe_like(root, "mdfe", ns_candidates, tipo)
        if tipo == "Evento":
            return self._parse_evento(root, ns_candidates)

        # Tentativa: NFSe (muitos layouts têm root "CompNfse"/"Nfse")
        if tipo == "NFS-e" or self._looks_like_nfse(root, ns_candidates):
            return self._parse_nfse(root, ns_candidates)

        return {"erro": f"Tipo de documento não identificado (tag='{tag}')"}

    # --------------------------- Parsers ---------------------------
    def _parse_nfe_like(self, root: ET.Element, ns_key: str, ns_candidates: Dict[str, str], tipo: str) -> Dict[str, Any]:
        ns = {ns_key: ns_candidates.get(ns_key, self.BASE_NS[ns_key])}
        # inf tag: infNFe / infCte / infMDFe
        inf_tag = {
            "nfe": "infNFe",
            "cte": "infCte",
            "mdfe": "infMDFe",
        }[ns_key]

        ide_tag = "ide"

        inf = root.find(f".//{ns_key}:{inf_tag}", ns)
        chave = None
        if inf is not None:
            _id = inf.attrib.get("Id")
            if _id:
                # remove prefixo NFe/CTe/MDFe
                chave = _id.replace("NFe", "").replace("CTe", "").replace("MDFe", "")

        emit_cnpj = _text(root.find(f".//{ns_key}:emit/{ns_key}:CNPJ", ns))
        emit_cpf = _text(root.find(f".//{ns_key}:emit/{ns_key}:CPF", ns))

        # destinatário (para MDF-e pode não existir – mantemos None)
        dest = _text(root.find(f".//{ns_key}:dest/{ns_key}:CNPJ", ns)) or _text(
            root.find(f".//{ns_key}:dest/{ns_key}:CPF", ns)
        )

        # data emissão – alguns XMLs antigos usam dEmi (sem hora)
        dh_emi = _text(root.find(f".//{ns_key}:{ide_tag}/{ns_key}:dhEmi", ns)) or _text(
            root.find(f".//{ns_key}:{ide_tag}/{ns_key}:dEmi", ns)
        )

        # protocolo (quando proc*)
        prot_paths = {
            "nfe": ".//nfe:protNFe/nfe:infProt/nfe:nProt",
            "cte": ".//cte:protCTe/cte:infProt/cte:nProt",
            "mdfe": ".//mdfe:protMDFe/mdfe:infProt/mdfe:nProt",
        }
        prot_ns = {
            "nfe": {"nfe": ns["nfe"]},
            "cte": {"cte": ns.get("cte", self.BASE_NS["cte"])},
            "mdfe": {"mdfe": ns.get("mdfe", self.BASE_NS["mdfe"])},
        }
        protocolo = _text(root.find(prot_paths[ns_key], prot_ns[ns_key]))

        return {
            "tipo_documento": tipo,
            "chave_acesso": chave,
            "cnpj_emitente": emit_cnpj,
            "cpf_emitente": emit_cpf,
            "destinatario": dest,
            "data_emissao": self._normalize_datetime(dh_emi),
            "protocolo": protocolo,
        }

    def _parse_evento(self, root: ET.Element, ns_candidates: Dict[str, str]) -> Dict[str, Any]:
        ns = {"nfe": ns_candidates.get("nfe", self.BASE_NS["nfe"])}
        ch = _text(root.find(".//nfe:chNFe", ns))
        tp = _text(root.find(".//nfe:tpEvento", ns)) or _text(root.find(".//nfe:detEvento/nfe:descEvento", ns))
        seq = _text(root.find(".//nfe:nSeqEvento", ns))
        cnpj = _text(root.find(".//nfe:CNPJ", ns))
        cpf = _text(root.find(".//nfe:CPF", ns))
        dh = _text(root.find(".//nfe:dhEvento", ns))
        prot = _text(root.find(".//nfe:nProt", ns))
        return {
            "tipo_documento": "Evento",
            "isevent": "1",
            "chave_acesso": ch,
            "tipo_evento": tp,
            "sequencia_evento": seq,
            "cnpj_emitente": cnpj,
            "cpf_emitente": cpf,
            "data_evento": self._normalize_datetime(dh),
            "protocolo": prot,
        }

    def _parse_nfse(self, root: ET.Element, ns_candidates: Dict[str, str]) -> Dict[str, Any]:
        """Parser tolerante a variações ABRASF (CompNfse/Nfse, caminhos e namespaces)."""
        # escolha do namespace – tenta candidatos do documento, depois variantes conhecidas
        nfse_ns_uri = ns_candidates.get("nfse")
        if nfse_ns_uri is None or nfse_ns_uri not in self.NFSE_VARIANTS:
            # força uma variante conhecida para xpath
            nfse_ns_uri = self.NFSE_VARIANTS[0]
        ns = {"nfse": nfse_ns_uri}

        # Correções: tags podem vir com capitalização/mudanças leves (Numero vs número etc.)
        # Estruturas mais frequentes:
        #   CompNfse/Nfse/InfNfse
        #   Nfse/InfNfse
        # Numero pode estar em InfNfse/Numero ou IdentificacaoNfse/Numero
        # PrestadorServico/IdentificacaoPrestador/(Cnpj|CpfCnpj/Cnpj|CpfCnpj/Cpf)
        # TomadorServico/IdentificacaoTomador/(Cnpj|CpfCnpj/Cnpj|CpfCnpj/Cpf)

        # Achar nó base InfNfse
        inf = (
            root.find(".//nfse:InfNfse", ns)
            or root.find(".//nfse:InfNFSe", ns)
            or root.find(".//nfse:infNfse", ns)
        )

        # Numero (chave da NFSe)
        numero = _text(root.find(".//nfse:IdentificacaoNfse/nfse:Numero", ns))
        if not numero and inf is not None:
            numero = _text(inf.find("nfse:Numero", ns))

        # Data de emissão
        data_emissao = _text(root.find(".//nfse:DataEmissao", ns))
        if not data_emissao and inf is not None:
            data_emissao = _text(inf.find("nfse:DataEmissao", ns))

        # Prestador (emitente)
        emit = (
            _text(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:Cnpj", ns))
            or _text(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:CpfCnpj/nfse:Cnpj", ns))
            or _text(root.find(".//nfse:PrestadorServico/nfse:IdentificacaoPrestador/nfse:CpfCnpj/nfse:Cpf", ns))
        )

        # Tomador (destinatário)
        dest = (
            _text(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:Cnpj", ns))
            or _text(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:Cpf", ns))
            or _text(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cnpj", ns))
            or _text(root.find(".//nfse:TomadorServico/nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cpf", ns))
        )

        return {
            "tipo_documento": "NFS-e",
            "chave_acesso": numero,
            "cnpj_emitente": emit,
            "destinatario": dest,
            "data_emissao": self._normalize_datetime(data_emissao),
            "protocolo": numero,  # muitas prefeituras usam o mesmo número como protocolo
        }

    # --------------------------- Utilidades ---------------------------
    def _looks_like_nfse(self, root: ET.Element, ns_candidates: Dict[str, str]) -> bool:
        tag = _local_name(root.tag)
        if tag in {"compnfse", "comppnfse", "nfse"}:
            return True
        # Heurística: se há DataEmissao + PrestadorServico no doc
        ns = {"nfse": ns_candidates.get("nfse", self.BASE_NS["nfse"]) }
        has_nfse_signals = bool(
            root.find(".//nfse:PrestadorServico", ns) is not None
            or root.find(".//nfse:TomadorServico", ns) is not None
            or root.find(".//nfse:InfNfse", ns) is not None
        )
        return has_nfse_signals

    def _normalize_datetime(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            # aceita "YYYY-MM-DD" ou ISO completo
            if "T" in value:
                # remove timezone se presente (ElementTree não converte TZ)
                try:
                    # 2025-08-14T02:23:33-03:00 -> 2025-08-14 02:23:33
                    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                except Exception:
                    pass
            # fallback: só data
            return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            # se formato muito irregular, devolve como veio
            return value

    def _collect_namespaces(self, root: ET.Element) -> Dict[str, str]:
        # Não há nsmap no ElementTree puro; deduz da própria árvore via atributos xmlns
        ns = dict(self.BASE_NS)
        # percorre poucas camadas – suficiente e barato
        to_scan = [root] + list(root)[:10]
        for el in to_scan:
            # atributos do namespace padrão e prefixados
            for k, v in el.attrib.items():
                # nada aqui
                _ = (k, v)
            # ElementTree não expõe xmlns* em attrib; como fallback mantemos BASE_NS
            # Alguns fornecedores embutem o namespace no próprio tag; extraímos por inspeção
            if "}" in el.tag:
                uri = el.tag.split("}")[0].strip("{")
                lname = _local_name(el.tag)
                if uri in self.NFSE_VARIANTS:
                    ns["nfse"] = uri
                elif uri == self.BASE_NS["nfe"]:
                    ns["nfe"] = uri
                elif uri == self.BASE_NS["cte"]:
                    ns["cte"] = uri
                elif uri == self.BASE_NS["mdfe"]:
                    ns["mdfe"] = uri
        return ns


# --------------------------- Funções de entrada ---------------------------
# Para usar na AWS Lambda sem criar objeto manualmente
_parser_singleton: Optional[DocumentoFiscalParser] = None

def handler(event, context):
    global _parser_singleton
    if _parser_singleton is None:
        _parser_singleton = DocumentoFiscalParser()
    return _parser_singleton.lambda_handler(event, context)
