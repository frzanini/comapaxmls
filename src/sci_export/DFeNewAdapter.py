from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict, Optional, List
import xml.etree.ElementTree as ET

from domain import NFeNota, NFeItem
from utils import only_digits


class DFeNewAdapter:
    """
    Adapter para usar DFeNew (DocumentoFiscalParser) quando disponível,
    com fallback para parser interno de NF-e.
    A saída (NFeNota/NFeItem) foi ampliada para cobrir os campos requeridos
    pelos layouts SCI: Anexo 04, Anexo 07 (C170) e Anexo 09.
    """

    def __init__(self) -> None:
        self._parser = None
        try:
            # from dfe.DocumentoFiscalParser import DocumentoFiscalParser  # type: ignore
            from DFeNew import DFeNew  # type: ignore
            self._parser = DFeNew()
        except Exception:
            self._parser = None

    # ------------------------------
    # API pública
    # ------------------------------
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

    # ------------------------------
    # Helpers
    # ------------------------------
    @staticmethod
    def _dec(v: Any, default: str = "0") -> Decimal:
        try:
            if v is None:
                return Decimal(default)
            return Decimal(str(v))
        except Exception:
            return Decimal(default)

    @staticmethod
    def _ymd(s: str) -> str:
        """Normaliza datas 'YYYY-MM-DD...' para 'YYYYMMDD'."""
        if not s:
            return ""
        s = str(s)
        if len(s) >= 10 and "-" in s:
            return f"{s[0:4]}{s[5:7]}{s[8:10]}"
        return s[0:8]

    # ------------------------------
    # Mapeamento via DFeNew
    # ------------------------------
    def _map_from_dfenew(self, data: Dict[str, Any]) -> NFeNota:
        dec = self._dec

        # Cabeçalho
        nota = NFeNota(
            chave=only_digits(data.get("chave_acesso") or data.get("chave") or ""),
            modelo=str(data.get("modelo") or "55"),
            serie=str(data.get("serie") or ""),
            numero=str(data.get("numero") or ""),
            cnpj_emit=only_digits(data.get("cnpj_emitente") or data.get("cpf_emitente") or ""),
            cnpj_dest=only_digits(data.get("cnpj_destinatario") or data.get("cpf_destinatario") or ""),
            uf_emit=str(data.get("uf_emitente") or data.get("uf") or ""),
            uf_dest=str(data.get("uf_destinatario") or ""),
            ie_emit=str(
                data.get("ie_emitente")
                or data.get("inscricao_estadual_emitente")
                or data.get("ie_emit")
                or ""
            ).strip(),
            ie_dest=str(
                data.get("ie_destinatario")
                or data.get("inscricao_estadual_destinatario")
                or data.get("ie_dest")
                or ""
            ).strip(),
            data_emissao=self._ymd(data.get("data_emissao_fmt") or data.get("data_emissao") or ""),
            data_entrada=self._ymd(data.get("data_entrada_fmt") or data.get("data_entrada") or ""),
            v_bc_icms=dec(data.get("v_bc_icms")),
            v_icms=dec(data.get("v_icms")),
            v_ipi=dec(data.get("v_ipi")),
            v_desc=dec(data.get("v_desc")),
            v_frete=dec(data.get("v_frete")),
            v_seg=dec(data.get("v_seg")),
            v_outros=dec(data.get("v_outros")),
            v_pis=dec(data.get("v_pis")),
            v_cofins=dec(data.get("v_cofins")),
            especie=str(data.get("especie") or "NF"),
            serie_doc=str(data.get("serie") or ""),
            modelo_doc=str(data.get("modelo") or "55"),
            nat_oper=str(data.get("nat_oper") or data.get("natop") or ""),
            ind_final=data.get("ind_final"),
            ind_pres=data.get("ind_pres"),
            cfops=list(self._coletar_cfops(data.get("itens") or [])),
            chaves_cte=list(self._coletar_chaves_cte(data)),
            frete_modalidade=self._frete_modalidade(data),
            valor_frete_doc=dec(data.get("v_frete")),
            di_numero=str(data.get("di_numero") or ""),
            di_moeda=data.get("di_moeda"),
            di_valor_brl=dec(data.get("di_valor_brl")),
            di_valor_moeda=dec(data.get("di_valor_moeda")),
            observacao=str(data.get("observacao") or data.get("infCpl") or ""),
            items=[],
        )

        # Itens
        itens_in = data.get("itens") or []
        for i, it in enumerate(itens_in):
            n_item = int(it.get("n_item") or i + 1)
            item = NFeItem(
                n_item=n_item,
                c_prod=str(it.get("cProd") or it.get("codigo") or ""),
                cfop=str(it.get("CFOP") or it.get("cfop") or ""),
                u_com=str(it.get("uCom") or it.get("unidade") or ""),
                q_com=dec(it.get("qCom") or it.get("quantidade")),
                v_un_com=dec(it.get("vUnCom") or it.get("valor_unit")),
                v_prod=dec(it.get("vProd") or it.get("valor_total")),
                cst_icms=str(it.get("CST") or it.get("CSOSN") or ""),
                p_icms=dec(it.get("pICMS")),
                v_bc_icms=dec(it.get("vBC")),
                v_icms=dec(it.get("vICMS")),
                v_bc_st=dec(it.get("vBCST")),
                p_icms_st=dec(it.get("pICMSST")),
                v_icms_st=dec(it.get("vICMSST")),
                v_ipi=dec(it.get("vIPI")),
                p_ipi=dec(it.get("pIPI")),
                p_pis=dec(it.get("pPIS")),
                v_pis=dec(it.get("vPIS")),
                p_cofins=dec(it.get("pCOFINS")),
                v_cofins=dec(it.get("vCOFINS")),
                cst_pis=str(it.get("CST_PIS") or it.get("cst_pis") or ""),
                cst_cofins=str(it.get("CST_COFINS") or it.get("cst_cofins") or ""),
                cst_ipi=str(it.get("CST_IPI") or it.get("cst_ipi") or ""),
                aliq_st_sped=dec(it.get("aliquota_st_sped")),
                conta_analitica_sped=str(it.get("conta_analitica_sped") or ""),
                despesas_acessorias=dec(it.get("despesas_acessorias")),
                icms_st_deduzir=dec(it.get("icms_st_deduzir")),
                icms_st_completar=dec(it.get("icms_st_completar")),
                base_retencao=dec(it.get("base_retencao")),
                parcela_imposto_retido=dec(it.get("parcela_imposto_retido")),
                aliq_funrural=dec(it.get("aliq_funrural")),
                v_funrural=dec(it.get("v_funrural")),
                icms_funrural=dec(it.get("icms_funrural")),
                base_fcp_st=dec(it.get("base_fcp_st")),
                p_fcp_st=dec(it.get("p_fcp_st")),
                v_fcp_st=dec(it.get("v_fcp_st")),
                base_fcp=dec(it.get("base_fcp")),
                p_fcp=dec(it.get("p_fcp")),
                v_fcp=dec(it.get("v_fcp")),
                qtd_convertida=dec(it.get("qtd_convertida")),
                unid_convertida=str(it.get("unid_convertida") or ""),
                v_unit_convertido=dec(it.get("v_unit_convertido")),
                credito_icms_unit_convertido=dec(it.get("credito_icms_unit_convertido")),
                base_st_unit_convertida=dec(it.get("base_st_unit_convertida")),
                icms_st_fcp_unit_convertido=dec(it.get("icms_st_fcp_unit_convertido")),
                fcp_st_unit_convertido=dec(it.get("fcp_st_unit_convertido")),
            )
            nota.items.append(item)

        # Quebra por alíquotas (opcional, se DFeNew trouxer)
        icms_aliqs = data.get("icms_por_aliquota") or {}
        for aliq, payload in icms_aliqs.items():
            nota.icms_por_aliquota[str(aliq)] = {
                "base": dec(payload.get("base")),
                "icms": dec(payload.get("icms")),
                "red_pct": dec(payload.get("red_pct")),
            }

        # Placas (se vierem do parser externo)
        placas = data.get("placas") or []
        if len(placas) >= 1:
            nota.placa1 = str(placas[0].get("placa") or "")
            nota.uf_placa1 = str(placas[0].get("uf") or "")
        if len(placas) >= 2:
            nota.placa2 = str(placas[1].get("placa") or "")
            nota.uf_placa2 = str(placas[1].get("uf") or "")
        if len(placas) >= 3:
            nota.placa3 = str(placas[2].get("placa") or "")
            nota.uf_placa3 = str(placas[2].get("uf") or "")

        return nota

    @staticmethod
    def _coletar_cfops(itens: List[Dict[str, Any]]) -> List[str]:
        cfops = []
        for it in itens:
            c = (it.get("CFOP") or it.get("cfop") or "").strip()
            if c:
                cfops.append(c)
        return list(dict.fromkeys(cfops))  # unique e mantém ordem

    @staticmethod
    def _coletar_chaves_cte(data: Dict[str, Any]) -> List[str]:
        chaves = []
        for key in ("cte_chave", "chaves_cte", "cte_referenciados"):
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                chaves.append(v.strip())
            elif isinstance(v, list):
                chaves.extend([str(x).strip() for x in v if str(x).strip()])
        return list(dict.fromkeys(chaves))

    @staticmethod
    def _frete_modalidade(data: Dict[str, Any]) -> Optional[int]:
        # tenta padronizar 0/1/2/9
        fm = data.get("frete_modalidade")
        try:
            return int(fm) if fm is not None and str(fm).isdigit() else None
        except Exception:
            return None

    # ------------------------------
    # Parser interno (NF-e)
    # ------------------------------
    def _parse_internal(self, xml_text: str) -> NFeNota:
        NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
        root = ET.fromstring(xml_text)
        inf = root.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
        if inf is None:
            raise ValueError("XML NFe inválido (infNFe não encontrado)")

        def _t(node: Optional[ET.Element], tag: str) -> str:
            if node is None:
                return ""
            el = node.find(f"nfe:{tag}", NS)
            return el.text.strip() if el is not None and el.text else ""

        def _d(node: Optional[ET.Element], tag: str) -> Decimal:
            s = _t(node, tag)
            return Decimal(s) if s else Decimal("0")

        def _ymd(s: str) -> str:
            if not s:
                return ""
            return f"{s[0:4]}{s[5:7]}{s[8:10]}"

        # Blocos principais
        ide = inf.find("nfe:ide", NS)
        emit = inf.find("nfe:emit", NS)
        dest = inf.find("nfe:dest", NS)
        total = inf.find("nfe:total/nfe:ICMSTot", NS)
        transp = inf.find("nfe:transp", NS)

        nota = NFeNota()

        # Identificação
        nota.chave = only_digits(inf.attrib.get("Id", "").replace("NFe", ""))
        nota.modelo = _t(ide, "mod") or "55"
        nota.serie = _t(ide, "serie")
        nota.numero = _t(ide, "nNF")
        nota.data_emissao = _ymd(_t(ide, "dhEmi") or _t(ide, "dEmi"))
        nota.data_entrada = _ymd(_t(ide, "dhSaiEnt") or _t(ide, "dSaiEnt") or _t(ide, "dhEmi") or _t(ide, "dEmi"))
        nota.nat_oper = _t(ide, "natOp")

        # Partes
        nota.cnpj_emit = only_digits(_t(emit, "CNPJ") or _t(emit, "CPF"))
        nota.cnpj_dest = only_digits(_t(dest, "CNPJ") or _t(dest, "CPF"))

        ender_emit = emit.find("nfe:enderEmit", NS) if emit is not None else None
        ender_dest = dest.find("nfe:enderDest", NS) if dest is not None else None
        nota.uf_emit = _t(ender_emit, "UF")
        nota.uf_dest = _t(ender_dest, "UF")

        # Totais
        if total is not None:
            nota.v_bc_icms = _d(total, "vBC")
            nota.v_icms = _d(total, "vICMS")
            nota.v_ipi = _d(total, "vIPI")
            nota.v_desc = _d(total, "vDesc")
            nota.v_frete = _d(total, "vFrete")
            nota.v_seg = _d(total, "vSeg")
            nota.v_outros = _d(total, "vOutro")
            nota.v_pis = _d(total, "vPIS")
            nota.v_cofins = _d(total, "vCOFINS")

        nota.especie = "NF"
        nota.serie_doc = nota.serie
        nota.modelo_doc = nota.modelo

        # Consumidor final / presença
        try:
            ind_final = _t(ide, "indFinal")
            nota.ind_final = int(ind_final) if ind_final.isdigit() else None
        except Exception:
            pass
        try:
            ind_pres = _t(ide, "indPres")
            nota.ind_pres = int(ind_pres) if ind_pres.isdigit() else None
        except Exception:
            pass

        # Transporte / frete
        if transp is not None:
            mod_frete = _t(transp, "modFrete")
            if mod_frete.isdigit():
                nota.frete_modalidade = int(mod_frete)
            # Placas
            veic = transp.find("nfe:veicTransp", NS)
            if veic is not None:
                nota.placa1 = _t(veic, "placa")
                nota.uf_placa1 = _t(veic, "UF")

        # Itens
        cfops_set = []
        for det in inf.findall("nfe:det", NS):
            n_item = int(det.attrib.get("nItem", "0") or 0)
            prod = det.find("nfe:prod", NS)
            imp = det.find("nfe:imposto", NS)

            it = NFeItem(n_item=n_item)

            if prod is not None:
                it.c_prod = _t(prod, "cProd")
                it.cfop = _t(prod, "CFOP")
                it.u_com = _t(prod, "uCom")
                it.q_com = _d(prod, "qCom")
                it.v_un_com = _d(prod, "vUnCom")
                it.v_prod = _d(prod, "vProd")
                if it.cfop:
                    cfops_set.append(it.cfop)

            if imp is not None:
                # ICMS
                icms_parent = imp.find("nfe:ICMS", NS)
                if icms_parent is not None and len(icms_parent):
                    icms = next(iter(icms_parent))
                    it.cst_icms = _t(icms, "CST") or _t(icms, "CSOSN")
                    it.p_icms = _d(icms, "pICMS")
                    it.v_bc_icms = _d(icms, "vBC")
                    it.v_icms = _d(icms, "vICMS")
                    it.v_bc_st = _d(icms, "vBCST")
                    it.p_icms_st = _d(icms, "pICMSST")
                    it.v_icms_st = _d(icms, "vICMSST")

                    # FCP (se existir nos nós de ICMS modernos)
                    it.base_fcp = _d(icms, "vBCFCP")
                    it.p_fcp = _d(icms, "pFCP")
                    it.v_fcp = _d(icms, "vFCP")
                    it.base_fcp_st = _d(icms, "vBCFCPST")
                    it.p_fcp_st = _d(icms, "pFCPST")
                    it.v_fcp_st = _d(icms, "vFCPST")

                # IPI
                ipi = imp.find("nfe:IPI", NS)
                if ipi is not None:
                    node = ipi.find("nfe:IPITrib", NS) or ipi.find("nfe:IPINT", NS)
                    if node is not None:
                        it.v_ipi = _d(node, "vIPI")
                        it.p_ipi = _d(node, "pIPI")
                        # tentativa de capturar CST IPI
                        cst_ipi = _t(node, "CST")
                        if cst_ipi:
                            it.cst_ipi = cst_ipi

                # PIS
                pis = imp.find("nfe:PIS", NS)
                if pis is not None and len(pis):
                    node = next(iter(pis))
                    it.p_pis = _d(node, "pPIS")
                    it.v_pis = _d(node, "vPIS")
                    cst_pis = _t(node, "CST")
                    if cst_pis:
                        it.cst_pis = cst_pis

                # COFINS
                cof = imp.find("nfe:COFINS", NS)
                if cof is not None and len(cof):
                    node = next(iter(cof))
                    it.p_cofins = _d(node, "pCOFINS")
                    it.v_cofins = _d(node, "vCOFINS")
                    cst_cof = _t(node, "CST")
                    if cst_cof:
                        it.cst_cofins = cst_cof

            nota.items.append(it)

        # CFOPs únicos em ordem
        nota.cfops = list(dict.fromkeys(cfops_set))

        # Observação/infCpl
        inf_adic = inf.find("nfe:infAdic", NS)
        if inf_adic is not None:
            obs = _t(inf_adic, "infCpl")
            if obs:
                nota.observacao = obs

        return nota
