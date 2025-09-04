from __future__ import annotations

"""
Gerador de arquivos TXT (SCI) para:
 - ANEXO 04 — Movimento de Saídas (linha por nota)
 - ANEXO 07 — Movimento de Produtos (Registro C170 do SPED — linha por item)
 - ANEXO 09 — Movimento de Entradas (linha por nota)

Entrada: diretórios/arquivos XML (NF-e modelo 55). Saída: arquivos .txt em disco.

Design
------
- Parser isolado (NFeParser) -> modelos de domínio (NFeNota, NFeItem)
- Engine de layout genérica: FieldType, LayoutField, Layout e Formatter
- Generators específicos de cada anexo, mapeando domínios -> colunas do layout
- CLI simples via argparse: apontar pasta/arquivo e saída

Observações importantes
-----------------------
- Regras de formatação segundo os layouts SCI: um registro por linha; campos
  separados por vírgula; alfanuméricos entre aspas; numéricos com ponto decimal;
  inteiros sem aspas; lógicos "Sim"/"Não".
- Muitos campos possuem dezenas/centenas de colunas. Para acelerar a adoção,
  este módulo entrega mapeamentos completos para os campos mais usuais
  (identificação, datas, valores principais) e zera/outros-vazios para os demais.
  Os layouts são definidos como listas ordenadas de LayoutField, então você pode
  ajustar e ampliar sem quebrar a compatibilidade do formatter.
- O parser cobre NF-e (modelo 55). Para outros modelos (CT-e 57, etc.),
  expanda NFeParser ou crie novos parsers especializados.

Compatibilidade
---------------
- Python 3.10+
- Apenas stdlib. Pydantic é OPCIONAL: se instalado, valida instâncias (sem exigir).

Uso rápido (CLI)
----------------
python sci_export.py --input "./xmls" --output "./out" --anexo 04 --anexo 07 --anexo 09

F5 no VS Code (sem args)
------------------------
- Usa defaults:
  - SCI_INPUT  = ./xmls   (ou defina no ambiente)
  - SCI_OUTPUT = ./out    (ou defina no ambiente)
  - Anexos 04,07,09
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence
import argparse
import logging
import xml.etree.ElementTree as ET

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
log = logging.getLogger("sci_export")
if not log.handlers:
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(fmt)
    log.addHandler(handler)
log.setLevel(logging.INFO)

# ----------------------------------------------------------------------------
# Domain models (lightweight; pydantic optional)
# ----------------------------------------------------------------------------
try:  # pydantic é opcional
    from pydantic import BaseModel

    class _BaseModel(BaseModel):
        model_config = {
            "extra": "ignore",
            "arbitrary_types_allowed": True,
        }

except Exception:  # noqa: BLE001

    @dataclass
    class _BaseModel:  # type: ignore
        """Fallback leve no lugar do pydantic.BaseModel."""

        def model_dump(self):  # compat de uso interno
            return self.__dict__


class NFeItem(_BaseModel):
    n_item: int
    c_prod: str = ""
    cfop: str = ""
    u_com: str = ""
    q_com: Decimal = Decimal("0")
    v_un_com: Decimal = Decimal("0")
    v_prod: Decimal = Decimal("0")
    cst_icms: str = ""  # CST ou CSOSN
    p_icms: Decimal = Decimal("0")
    v_bc_icms: Decimal = Decimal("0")
    v_icms: Decimal = Decimal("0")
    v_bc_st: Decimal = Decimal("0")
    p_icms_st: Decimal = Decimal("0")
    v_icms_st: Decimal = Decimal("0")
    v_ipi: Decimal = Decimal("0")
    p_ipi: Decimal = Decimal("0")
    p_pis: Decimal = Decimal("0")
    v_pis: Decimal = Decimal("0")
    p_cofins: Decimal = Decimal("0")
    v_cofins: Decimal = Decimal("0")


class NFeNota(_BaseModel):
    chave: str = ""
    modelo: str = "55"
    serie: str = ""
    numero: str = ""

    cnpj_emit: str = ""
    uf_emit: str = ""
    ie_dest: str = ""  # quando disponível
    cnpj_dest: str = ""  # cliente

    data_emissao: str = ""  # AAAAMMDD
    data_entrada: str = ""  # AAAAMMDD (ou saída)

    v_bc_icms: Decimal = Decimal("0")
    v_icms: Decimal = Decimal("0")
    v_ipi: Decimal = Decimal("0")
    v_desc: Decimal = Decimal("0")
    v_frete: Decimal = Decimal("0")
    v_seg: Decimal = Decimal("0")
    v_outros: Decimal = Decimal("0")
    v_pis: Decimal = Decimal("0")
    v_cofins: Decimal = Decimal("0")

    items: List[NFeItem] = ()  # type: ignore


# ----------------------------------------------------------------------------
# XML -> Domain parser
# ----------------------------------------------------------------------------
class NFeParser:
    """Parser de NF-e (modelo 55) para modelos de domínio.

    Aceita tanto NFe isolado quanto nfeProc.
    """

    NS = {
        "nfe": "http://www.portalfiscal.inf.br/nfe",
    }

    def parse_file(self, path: Path) -> NFeNota:
        tree = ET.parse(path)
        root = tree.getroot()

        # Localiza o nó infNFe independente de wrapper
        inf = root.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe")
        if inf is None:
            raise ValueError(f"XML inválido (infNFe não encontrado): {path}")

        nota = NFeNota()
        nota.chave = inf.attrib.get("Id", "").replace("NFe", "")

        ide = inf.find("nfe:ide", self.NS)
        emit = inf.find("nfe:emit", self.NS)
        dest = inf.find("nfe:dest", self.NS)
        total = inf.find("nfe:total/nfe:ICMSTot", self.NS)

        def _t(node: Optional[ET.Element], tag: str) -> str:
            if node is None:
                return ""
            el = node.find(f"nfe:{tag}", self.NS)
            return el.text.strip() if el is not None and el.text else ""

        # ide
        nota.modelo = _t(ide, "mod") or "55"
        nota.serie = _t(ide, "serie")
        nota.numero = _t(ide, "nNF")

        # Datas: preferir dhEmi/dhSaiEnt (AAAA-MM-DDTHH:MM:SS-03:00) -> AAAAMMDD
        dh_emi = _t(ide, "dhEmi") or _t(ide, "dEmi")
        dh_ent = _t(ide, "dhSaiEnt") or _t(ide, "dSaiEnt") or dh_emi

        def _to_ymd(s: str) -> str:
            if not s:
                return ""
            # aceita AAAA-MM-DD... ou AAAA-MM-DDThh:mm:ss-03:00
            yyyy = s[0:4]
            mm = s[5:7]
            dd = s[8:10]
            return f"{yyyy}{mm}{dd}"

        nota.data_emissao = _to_ymd(dh_emi)
        nota.data_entrada = _to_ymd(dh_ent)

        # emit
        nota.cnpj_emit = _t(emit, "CNPJ") or _t(emit, "CPF")
        ender_emit = emit.find("nfe:enderEmit", self.NS) if emit is not None else None
        nota.uf_emit = _t(ender_emit, "UF")

        # dest
        nota.cnpj_dest = _t(dest, "CNPJ") or _t(dest, "CPF")
        nota.ie_dest = _t(dest, "IE")

        # totais
        def _d(node: Optional[ET.Element], tag: str) -> Decimal:
            s = _t(node, tag)
            return Decimal(s) if s else Decimal("0")

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

        # itens
        items: List[NFeItem] = []
        for det in inf.findall("nfe:det", self.NS):
            try:
                n_item = int(det.attrib.get("nItem", "0"))
            except Exception:  # noqa: BLE001
                n_item = 0
            prod = det.find("nfe:prod", self.NS)
            imposto = det.find("nfe:imposto", self.NS)

            it = NFeItem(n_item=n_item)
            if prod is not None:
                it.c_prod = _t(prod, "cProd")
                it.cfop = _t(prod, "CFOP")
                it.u_com = _t(prod, "uCom")
                it.q_com = Decimal(_t(prod, "qCom") or "0")
                it.v_un_com = Decimal(_t(prod, "vUnCom") or "0")
                it.v_prod = Decimal(_t(prod, "vProd") or "0")

            if imposto is not None:
                # ICMS (dentro de ICMS qualquer variante ICMSxx)
                icms = None
                icms_parent = imposto.find("nfe:ICMS", self.NS)
                if icms_parent is not None and len(icms_parent):
                    icms = next(iter(icms_parent))  # pega primeiro filho ICMS00/20/etc.
                if icms is not None:
                    it.cst_icms = (
                        _t(icms, "CST") or _t(icms, "CSOSN")
                    )
                    it.p_icms = Decimal(_t(icms, "pICMS") or "0")
                    it.v_bc_icms = Decimal(_t(icms, "vBC") or "0")
                    it.v_icms = Decimal(_t(icms, "vICMS") or "0")
                    it.v_bc_st = Decimal(_t(icms, "vBCST") or "0")
                    it.p_icms_st = Decimal(_t(icms, "pICMSST") or "0")
                    it.v_icms_st = Decimal(_t(icms, "vICMSST") or "0")

                ipi = imposto.find("nfe:IPI", self.NS)
                if ipi is not None:
                    ipi_tax = None
                    for tag in ("IPITrib", "IPINT"):
                        t = ipi.find(f"nfe:{tag}", self.NS)
                        if t is not None:
                            ipi_tax = t
                            break
                    if ipi_tax is not None:
                        it.v_ipi = Decimal(_t(ipi_tax, "vIPI") or "0")
                        it.p_ipi = Decimal(_t(ipi_tax, "pIPI") or "0")

                pis = imposto.find("nfe:PIS", self.NS)
                if pis is not None and len(pis):
                    pisn = next(iter(pis))
                    it.p_pis = Decimal(_t(pisn, "pPIS") or "0")
                    it.v_pis = Decimal(_t(pisn, "vPIS") or "0")

                cof = imposto.find("nfe:COFINS", self.NS)
                if cof is not None and len(cof):
                    cofn = next(iter(cof))
                    it.p_cofins = Decimal(_t(cofn, "pCOFINS") or "0")
                    it.v_cofins = Decimal(_t(cofn, "vCOFINS") or "0")

            items.append(it)

        nota.items = items
        return nota


# ----------------------------------------------------------------------------
# Layout/Formatter engine
# ----------------------------------------------------------------------------
class FieldType(str, Enum):
    A = "A"  # Alfanumérico (com aspas)
    N = "N"  # Numérico (ponto decimal)
    I = "I"  # Inteiro (sem aspas)
    L = "L"  # Lógico ("Sim"/"Não")


@dataclass
class LayoutField:
    name: str
    ftype: FieldType
    decimals: Optional[int] = None
    default: Any = ""


@dataclass
class Layout:
    name: str
    fields: List[LayoutField]


class Formatter:
    @staticmethod
    def fmt(field: LayoutField, value: Any) -> str:
        t = field.ftype
        if value is None:
            value = field.default

        if t == FieldType.A:
            s = "" if value is None else str(value)
            return f'"{s}"'

        if t == FieldType.I:
            try:
                return str(int(Decimal(str(value))))
            except Exception:  # noqa: BLE001
                return str(int(0))

        if t == FieldType.N:
            decs = field.decimals or 0
            q = Decimal("1").scaleb(-decs)  # 10^-decs
            try:
                d = Decimal(str(value)).quantize(q, rounding=ROUND_HALF_UP)
            except Exception:  # noqa: BLE001
                d = Decimal("0").quantize(q)
            s = f"{d:.{decs}f}" if decs > 0 else f"{d}"
            return s

        if t == FieldType.L:
            # aceita bool/str
            if isinstance(value, bool):
                return "Sim" if value else "Não"
            sval = str(value).strip().lower()
            if sval in {"s", "sim", "true", "1"}:
                return "Sim"
            if sval in {"n", "nao", "não", "false", "0"}:
                return "Não"
            return "Não" if not sval else "Sim"  # fallback

        raise ValueError(f"Tipo de campo desconhecido: {t}")

    @classmethod
    def emit_row(cls, layout: Layout, row: Dict[str, Any]) -> str:
        values = []
        for f in layout.fields:
            v = row.get(f.name, f.default)
            values.append(cls.fmt(f, v))
        return ",".join(values)


# ----------------------------------------------------------------------------
# Layouts (colunas) e mapeamentos (nota/itens -> dict de saída)
# ----------------------------------------------------------------------------

# === ANEXO 07 – REGISTRO C170 (por item) ==========================
ANEXO07_C170 = Layout(
    name="ANEXO 07 – C170 (Produtos)",
    fields=[
        LayoutField("num_item_nf", FieldType.I, default=0),  # 01
        LayoutField("cod_prod", FieldType.A, default=""),   # 02 Código/Apelido
        LayoutField("tipo_mov", FieldType.A, default="E"),  # 03 "E"/"S"
        LayoutField("cnpj_cpf_cliente", FieldType.A, default=""),  # 04
        LayoutField("ie_cliente", FieldType.I, default=0),   # 05 IE cliente
        LayoutField("num_nf", FieldType.I, default=0),       # 06 número NF
        LayoutField("data_nf", FieldType.A, default=""),    # 07 AAAAMMDD
        LayoutField("uf_nf", FieldType.A, default=""),      # 08 UF
        LayoutField("serie_nf", FieldType.A, default="1"),  # 09
        LayoutField("especie_nf", FieldType.A, default="NF"),  # 10
        LayoutField("modelo_nf", FieldType.N, decimals=0, default=55),  # 11
        LayoutField("qtd_total_item", FieldType.N, decimals=2, default=0),  # 12
        LayoutField("valor_total_item", FieldType.N, decimals=2, default=0),  # 13
        LayoutField("aliq_icms", FieldType.N, decimals=2, default=0),  # 14
        LayoutField("valor_ipi", FieldType.N, decimals=2, default=0),  # 15
        LayoutField("bc_icms", FieldType.N, decimals=2, default=0),    # 16
        LayoutField("bc_st", FieldType.N, decimals=2, default=0),      # 17
        LayoutField("valor_desc", FieldType.N, decimals=2, default=0), # 18
        LayoutField("cfop", FieldType.A, default=""),                 # 19
        LayoutField("cst_icms", FieldType.A, default=""),            # 20
        LayoutField("mov_fisica", FieldType.L, default=True),          # 21
        LayoutField("cst_cofins", FieldType.I, default=1),             # 22
        LayoutField("cst_pis", FieldType.I, default=1),                # 23
        LayoutField("cst_ipi", FieldType.I, default=1),                # 24
        LayoutField("aliq_ipi", FieldType.N, decimals=2, default=0),   # 25
        LayoutField("bc_ipi", FieldType.N, decimals=2, default=0),     # 26
        LayoutField("aliq_pis", FieldType.N, decimals=2, default=0),   # 27
        LayoutField("bc_pis", FieldType.N, decimals=2, default=0),     # 28
        LayoutField("valor_pis", FieldType.N, decimals=2, default=0),  # 29
        LayoutField("aliq_cofins", FieldType.N, decimals=2, default=0),# 30
        LayoutField("bc_cofins", FieldType.N, decimals=2, default=0),  # 31
        LayoutField("valor_cofins", FieldType.N, decimals=2, default=0),# 32
        LayoutField("valor_icms", FieldType.N, decimals=2, default=0), # 33
        LayoutField("aliq_st", FieldType.N, decimals=2, default=0),    # 34
        LayoutField("valor_st", FieldType.N, decimals=2, default=0),   # 35
        # ... (você pode estender com as demais colunas do anexo 07 sem alterar o gerador)
    ],
)


def map_item_to_c170(nota: NFeNota, item: NFeItem, tipo_mov: str) -> Dict[str, Any]:
    """Mapeia um item de NF-e para o registro C170 do anexo 07."""
    return {
        "num_item_nf": item.n_item,
        "cod_prod": item.c_prod,
        "tipo_mov": tipo_mov,  # "E" ou "S"
        "cnpj_cpf_cliente": nota.cnpj_dest or nota.cnpj_emit,
        "ie_cliente": int(nota.ie_dest or 0) if (nota.ie_dest or "").isdigit() else 0,
        "num_nf": int(nota.numero or 0),
        "data_nf": nota.data_emissao,
        "uf_nf": nota.uf_emit,
        "serie_nf": nota.serie,
        "especie_nf": "NF",
        "modelo_nf": int(nota.modelo or 55),
        "qtd_total_item": item.q_com,
        "valor_total_item": item.v_prod,
        "aliq_icms": item.p_icms,
        "valor_ipi": item.v_ipi,
        "bc_icms": item.v_bc_icms,
        "bc_st": item.v_bc_st,
        "valor_desc": Decimal("0"),
        "cfop": item.cfop,
        "cst_icms": item.cst_icms,
        "mov_fisica": True,
        "cst_cofins": 1,
        "cst_pis": 1,
        "cst_ipi": 1,
        "aliq_ipi": item.p_ipi,
        "bc_ipi": Decimal("0"),
        "aliq_pis": item.p_pis,
        "bc_pis": Decimal("0"),
        "valor_pis": item.v_pis,
        "aliq_cofins": item.p_cofins,
        "bc_cofins": Decimal("0"),
        "valor_cofins": item.v_cofins,
        "valor_icms": item.v_icms,
        "aliq_st": item.p_icms_st,
        "valor_st": item.v_icms_st,
    }


# === ANEXO 09 – ENTRADAS (por nota) ===============================
ANEXO09_ENTRADAS = Layout(
    name="ANEXO 09 – Movimento de Entradas",
    fields=[
        LayoutField("chave_import", FieldType.I, default=1),   # 01 (sequencial de importação)
        LayoutField("cnpj_cpf_cliente", FieldType.A, default=""),  # 02
        LayoutField("uf_emit", FieldType.A, default=""),      # 03
        LayoutField("data_entrada", FieldType.A, default=""), # 04 AAAAMMDD
        LayoutField("data_emissao", FieldType.A, default=""), # 05 AAAAMMDD
        LayoutField("num_nf", FieldType.I, default=0),         # 06
        LayoutField("especie_doc", FieldType.A, default="NF"),# 07
        LayoutField("serie", FieldType.A, default="1"),       # 08
        LayoutField("nat_oper", FieldType.A, default=""),     # 09 (CFOP opcional)
        LayoutField("valor_contabil", FieldType.N, decimals=2, default=0),  # 10
        LayoutField("origem_merc", FieldType.A, default="0"), # 11 (0/1/2)
        LayoutField("cst_icms", FieldType.A, default="00"),    # 12
        LayoutField("red_bc_icms", FieldType.N, decimals=4, default=0),    # 13
        LayoutField("bc_icms", FieldType.N, decimals=2, default=0),        # 14
        LayoutField("aliq_icms", FieldType.N, decimals=4, default=0),      # 15
        LayoutField("valor_icms", FieldType.N, decimals=2, default=0),     # 16
        LayoutField("isentas_icms", FieldType.N, decimals=2, default=0),   # 17
        LayoutField("outras_icms", FieldType.N, decimals=2, default=0),    # 18
        LayoutField("icms_st_flag", FieldType.A, default="N"),            # 19 "S"/"N"
        LayoutField("bc_icms_st", FieldType.N, decimals=2, default=0),     # 20
        LayoutField("aliq_icms_st", FieldType.N, decimals=4, default=0),   # 21
        LayoutField("valor_icms_st", FieldType.N, decimals=2, default=0),  # 22
        LayoutField("bc_ipi", FieldType.N, decimals=2, default=0),         # 23
        LayoutField("valor_ipi", FieldType.N, decimals=2, default=0),      # 24
        # ... campos adicionais podem ser estendidos gradualmente
    ],
)


def map_nota_to_entradas(nota: NFeNota, seq: int) -> Dict[str, Any]:
    """Nota -> registro de Entradas (campos principais)."""
    # Heurística simples para CFOP predominante: do primeiro item (se houver)
    cfop = nota.items[0].cfop if nota.items else ""
    return {
        "chave_import": seq,
        "cnpj_cpf_cliente": nota.cnpj_emit,  # fornecedor/emitente da entrada
        "uf_emit": nota.uf_emit,
        "data_entrada": nota.data_entrada,
        "data_emissao": nota.data_emissao,
        "num_nf": int(nota.numero or 0),
        "especie_doc": "NF",
        "serie": nota.serie or "1",
        "nat_oper": cfop or "",
        "valor_contabil": sum((i.v_prod for i in nota.items), start=Decimal("0")),
        "origem_merc": "0",
        "cst_icms": nota.items[0].cst_icms if nota.items else "00",
        "red_bc_icms": Decimal("0"),
        "bc_icms": nota.v_bc_icms,
        "aliq_icms": nota.items[0].p_icms if nota.items else Decimal("0"),
        "valor_icms": nota.v_icms,
        "isentas_icms": Decimal("0"),
        "outras_icms": Decimal("0"),
        "icms_st_flag": "S" if any(i.v_icms_st > 0 for i in nota.items) else "N",
        "bc_icms_st": sum((i.v_bc_st for i in nota.items), start=Decimal("0")),
        "aliq_icms_st": nota.items[0].p_icms_st if nota.items else Decimal("0"),
        "valor_icms_st": sum((i.v_icms_st for i in nota.items), start=Decimal("0")),
        "bc_ipi": Decimal("0"),
        "valor_ipi": nota.v_ipi,
    }


# === ANEXO 04 – SAÍDAS (por nota) ================================
# Observação: o layout de saídas é análogo ao de entradas nas primeiras colunas
# (identificação, datas, valores principais). Ajuste/estenda conforme o PDF.
ANEXO04_SAIDAS = Layout(
    name="ANEXO 04 – Movimento de Saídas",
    fields=[
        LayoutField("chave_import", FieldType.I, default=1),
        LayoutField("cnpj_cpf_cliente", FieldType.A, default=""),  # destinatário
        LayoutField("uf_emit", FieldType.A, default=""),
        LayoutField("data_saida", FieldType.A, default=""),   # usa data_entrada como saída
        LayoutField("data_emissao", FieldType.A, default=""),
        LayoutField("num_nf", FieldType.I, default=0),
        LayoutField("especie_doc", FieldType.A, default="NF"),
        LayoutField("serie", FieldType.A, default="1"),
        LayoutField("nat_oper", FieldType.A, default=""),     # CFOP principal
        LayoutField("valor_contabil", FieldType.N, decimals=2, default=0),
        LayoutField("cst_icms", FieldType.A, default="00"),
        LayoutField("bc_icms", FieldType.N, decimals=2, default=0),
        LayoutField("aliq_icms", FieldType.N, decimals=2, default=0),
        LayoutField("valor_icms", FieldType.N, decimals=2, default=0),
        LayoutField("valor_ipi", FieldType.N, decimals=2, default=0),
        LayoutField("valor_frete", FieldType.N, decimals=2, default=0),
        LayoutField("valor_seg", FieldType.N, decimals=2, default=0),
        LayoutField("valor_outras", FieldType.N, decimals=2, default=0),
        # ... estender com campos específicos do anexo 04
    ],
)


def map_nota_to_saidas(nota: NFeNota, seq: int) -> Dict[str, Any]:
    cfop = nota.items[0].cfop if nota.items else ""
    return {
        "chave_import": seq,
        "cnpj_cpf_cliente": nota.cnpj_dest,  # cliente/destinatário
        "uf_emit": nota.uf_emit,
        "data_saida": nota.data_entrada or nota.data_emissao,
        "data_emissao": nota.data_emissao,
        "num_nf": int(nota.numero or 0),
        "especie_doc": "NF",
        "serie": nota.serie or "1",
        "nat_oper": cfop or "",
        "valor_contabil": sum((i.v_prod for i in nota.items), start=Decimal("0")),
        "cst_icms": nota.items[0].cst_icms if nota.items else "00",
        "bc_icms": nota.v_bc_icms,
        "aliq_icms": nota.items[0].p_icms if nota.items else Decimal("0"),
        "valor_icms": nota.v_icms,
        "valor_ipi": nota.v_ipi,
        "valor_frete": nota.v_frete,
        "valor_seg": nota.v_seg,
        "valor_outras": nota.v_outros,
    }


# ----------------------------------------------------------------------------
# Writers
# ----------------------------------------------------------------------------
def write_rows(path: Path, layout: Layout, rows: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            line = Formatter.emit_row(layout, row)
            f.write(line + "\n")
            count += 1
    log.info("Gerado %s (%d linhas)", path, count)
    return count


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def _iter_xml_files(p: Path) -> Iterable[Path]:
    if p.is_file() and p.suffix.lower() in {".xml"}:
        yield p
    elif p.is_dir():
        for xp in sorted(p.rglob("*.xml")):
            yield xp


def run_cli():
    ap = argparse.ArgumentParser(description="Gerar TXT SCI a partir de XMLs DF-e")
    ap.add_argument("--input", required=True, help="Arquivo ou pasta com XMLs")
    ap.add_argument("--output", required=True, help="Pasta de saída")
    ap.add_argument(
        "--anexo",
        action="append",
        choices=["04", "07", "09"],
        help="Quais anexos gerar (pode repetir). Ex.: --anexo 04 --anexo 07",
    )
    args = ap.parse_args()

    inp = Path(args.input)
    outdir = Path(args.output)
    anexos = set(args.anexo or ["04", "07", "09"])  # padrão: todos

    parser = NFeParser()

    notas: List[NFeNota] = []
    for x in _iter_xml_files(inp):
        try:
            n = parser.parse_file(x)
            notas.append(n)
        except Exception as e:  # noqa: BLE001
            log.error("Falha ao parsear %s: %s", x, e)

    if not notas:
        log.warning("Nenhuma nota válida encontrada em %s", inp)
        return

    # ANEXO 07 – C170 (por item)
    if "07" in anexos:
        rows: List[Dict[str, Any]] = []
        for n in notas:
            tipo_mov = "E"  # Heurística simples, ajuste conforme regra de negócio
            for it in n.items:
                rows.append(map_item_to_c170(n, it, tipo_mov))
        write_rows(outdir / "anexo07_c170.txt", ANEXO07_C170, rows)

    # ANEXO 09 – Entradas (por nota)
    if "09" in anexos:
        rows = [map_nota_to_entradas(n, i + 1) for i, n in enumerate(notas)]
        write_rows(outdir / "anexo09_entradas.txt", ANEXO09_ENTRADAS, rows)

    # ANEXO 04 – Saídas (por nota)
    if "04" in anexos:
        rows = [map_nota_to_saidas(n, i + 1) for i, n in enumerate(notas)]
        write_rows(outdir / "anexo04_saidas.txt", ANEXO04_SAIDAS, rows)


# ----------------------------------------------------------------------------
# MAIN para F5 no VS Code (sem argumentos)
# ----------------------------------------------------------------------------
def main():
    """Permite rodar com F5 no VS Code sem passar argumentos.

    Defaults:
      - SCI_INPUT  = "./xmls"  (pasta com XMLs)
      - SCI_OUTPUT = "./out"   (pasta de saída)
      - Anexos 04, 07, 09
    """
    import os
    import sys

    if len(sys.argv) == 1:
        sys.argv += [
            "--input", os.getenv("SCI_INPUT", "./xmls"),
            "--output", os.getenv("SCI_OUTPUT", "./out"),
            "--anexo", "04", "--anexo", "07", "--anexo", "09",
        ]
    run_cli()


if __name__ == "__main__":
    main()
