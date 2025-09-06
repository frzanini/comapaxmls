from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict, Optional
import xml.etree.ElementTree as ET
from domain import NFeNota, NFeItem
from utils import only_digits

class DFeNewAdapter:
    """Adapter para usar DFeNew (DocumentoFiscalParser) quando disponível.
    Fallback para parser interno de NF-e caso o pacote não esteja acessível.
    """
    def __init__(self) -> None:
        self._parser = None
        try:
            #from dfe.DocumentoFiscalParser import DocumentoFiscalParser  # type: ignore
            from DFeNew import DFeNew  # type: ignore
            self._parser = DFeNew()
        except Exception:
            self._parser = None

    def parse(self, xml_text: str) -> NFeNota:
        if self._parser is None:
            return self._parse_internal(xml_text)
        try:
            data = self._parser.parse_string(xml_text)
            if not data or ("itens" not in data):
                return self._parse_internal(xml_text)
            return self._map_from_dfenew(data)
        except Exception:
            return self._parse_internal(xml_text)

    # --- Map DFeNew -> domínio ---
    def _map_from_dfenew(self, data: Dict[str, Any]) -> NFeNota:
        def dec(v: Any) -> Decimal:
            try:
                return Decimal(str(v))
            except Exception:
                return Decimal("0")
        nota = NFeNota(
            chave=only_digits(data.get("chave_acesso") or data.get("chave") or ""),
            modelo=str(data.get("modelo") or "55"),
            serie=str(data.get("serie") or ""),
            numero=str(data.get("numero") or ""),
            cnpj_emit=only_digits(data.get("cnpj_emitente") or data.get("cpf_emitente") or ""),
            cnpj_dest=only_digits(data.get("cnpj_destinatario") or data.get("cpf_destinatario") or ""),
            uf_emit=str(data.get("uf_emitente") or ""),
            data_emissao=str(data.get("data_emissao_fmt") or data.get("data_emissao") or "").replace("-", "")[0:8],
            data_entrada=str(data.get("data_entrada_fmt") or data.get("data_entrada") or "").replace("-", "")[0:8],
            v_bc_icms=dec(data.get("v_bc_icms")), v_icms=dec(data.get("v_icms")), v_ipi=dec(data.get("v_ipi")),
            v_desc=dec(data.get("v_desc")), v_frete=dec(data.get("v_frete")), v_seg=dec(data.get("v_seg")),
            v_outros=dec(data.get("v_outros")), v_pis=dec(data.get("v_pis")), v_cofins=dec(data.get("v_cofins")),
            items=[],
        )
        for i, it in enumerate(data.get("itens") or []):
            nota.items.append(NFeItem(
                n_item=int(it.get("n_item") or i + 1),
                c_prod=str(it.get("cProd") or it.get("codigo") or ""),
                cfop=str(it.get("CFOP") or it.get("cfop") or ""),
                u_com=str(it.get("uCom") or it.get("unidade") or ""),
                q_com=dec(it.get("qCom") or it.get("quantidade")),
                v_un_com=dec(it.get("vUnCom") or it.get("valor_unit")),
                v_prod=dec(it.get("vProd") or it.get("valor_total")),
                cst_icms=str(it.get("CST") or it.get("CSOSN") or ""),
                p_icms=dec(it.get("pICMS")), v_bc_icms=dec(it.get("vBC")), v_icms=dec(it.get("vICMS")),
                v_bc_st=dec(it.get("vBCST")), p_icms_st=dec(it.get("pICMSST")), v_icms_st=dec(it.get("vICMSST")),
                v_ipi=dec(it.get("vIPI")), p_ipi=dec(it.get("pIPI")), p_pis=dec(it.get("pPIS")), v_pis=dec(it.get("vPIS")),
                p_cofins=dec(it.get("pCOFINS")), v_cofins=dec(it.get("vCOFINS")),
            ))
        return nota

    # --- Parser interno (NF-e) ---
    def _parse_internal(self, xml_text: str) -> NFeNota:
        NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
        root = ET.fromstring(xml_text)
        inf = root.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
        if inf is None:
            raise ValueError("XML NFe inválido (infNFe não encontrado)")
        def _t(node: Optional[ET.Element], tag: str) -> str:
            if node is None: return ""
            el = node.find(f"nfe:{tag}", NS)
            return el.text.strip() if el is not None and el.text else ""
        def _ymd(s: str) -> str:
            if not s: return ""
            return f"{s[0:4]}{s[5:7]}{s[8:10]}"
        nota = NFeNota(items=[])
        nota.chave = only_digits(inf.attrib.get("Id", "").replace("NFe", ""))
        ide = inf.find("nfe:ide", NS); emit = inf.find("nfe:emit", NS); dest = inf.find("nfe:dest", NS)
        total = inf.find("nfe:total/nfe:ICMSTot", NS)
        nota.modelo = _t(ide, "mod") or "55"; nota.serie = _t(ide, "serie"); nota.numero = _t(ide, "nNF")
        dh_emi = _t(ide, "dhEmi") or _t(ide, "dEmi"); dh_ent = _t(ide, "dhSaiEnt") or _t(ide, "dSaiEnt") or dh_emi
        nota.data_emissao = _ymd(dh_emi); nota.data_entrada = _ymd(dh_ent)
        nota.cnpj_emit = only_digits(_t(emit, "CNPJ") or _t(emit, "CPF"))
        nota.cnpj_dest = only_digits(_t(dest, "CNPJ") or _t(dest, "CPF"))
        nota.uf_emit = _t(emit.find("nfe:enderEmit", NS) if emit is not None else None, "UF")
        def _d(node: Optional[ET.Element], tag: str) -> Decimal:
            s = _t(node, tag); return Decimal(s) if s else Decimal("0")
        if total is not None:
            nota.v_bc_icms = _d(total, "vBC"); nota.v_icms = _d(total, "vICMS"); nota.v_ipi = _d(total, "vIPI")
            nota.v_desc = _d(total, "vDesc"); nota.v_frete = _d(total, "vFrete"); nota.v_seg = _d(total, "vSeg")
            nota.v_outros = _d(total, "vOutro"); nota.v_pis = _d(total, "vPIS"); nota.v_cofins = _d(total, "vCOFINS")
        for det in inf.findall("nfe:det", NS):
            n_item = int(det.attrib.get("nItem", "0") or 0)
            prod = det.find("nfe:prod", NS); imp = det.find("nfe:imposto", NS)
            it = NFeItem(n_item=n_item)
            def D(node: Optional[ET.Element], tag: str) -> Decimal:
                if node is None: return Decimal("0")
                s = _t(node, tag); return Decimal(s) if s else Decimal("0")
            if prod is not None:
                it.c_prod = _t(prod, "cProd"); it.cfop = _t(prod, "CFOP"); it.u_com = _t(prod, "uCom")
                it.q_com = D(prod, "qCom"); it.v_un_com = D(prod, "vUnCom"); it.v_prod = D(prod, "vProd")
            if imp is not None:
                icms_parent = imp.find("nfe:ICMS", NS)
                if icms_parent is not None and len(icms_parent):
                    icms = next(iter(icms_parent))
                    it.cst_icms = _t(icms, "CST") or _t(icms, "CSOSN")
                    it.p_icms = D(icms, "pICMS"); it.v_bc_icms = D(icms, "vBC"); it.v_icms = D(icms, "vICMS")
                    it.v_bc_st = D(icms, "vBCST"); it.p_icms_st = D(icms, "pICMSST"); it.v_icms_st = D(icms, "vICMSST")
                ipi = imp.find("nfe:IPI", NS)
                if ipi is not None:
                    for tag in ("IPITrib", "IPINT"):
                        node = ipi.find(f"nfe:{tag}", NS)
                        if node is not None:
                            it.v_ipi = D(node, "vIPI"); it.p_ipi = D(node, "pIPI"); break
                pis = imp.find("nfe:PIS", NS)
                if pis is not None and len(pis):
                    node = next(iter(pis)); it.p_pis = D(node, "pPIS"); it.v_pis = D(node, "vPIS")
                cof = imp.find("nfe:COFINS", NS)
                if cof is not None and len(cof):
                    node = next(iter(cof)); it.p_cofins = D(node, "pCOFINS"); it.v_cofins = D(node, "vCOFINS")
            nota.items.append(it)
        return nota
