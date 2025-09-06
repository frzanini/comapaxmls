from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import List


@dataclass
class NFeItem:
    n_item: int
    c_prod: str = ""
    cfop: str = ""
    u_com: str = ""
    q_com: Decimal = Decimal("0")
    v_un_com: Decimal = Decimal("0")
    v_prod: Decimal = Decimal("0")
    cst_icms: str = ""
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


@dataclass
class NFeNota:
    chave: str = ""
    modelo: str = "55"
    serie: str = ""
    numero: str = ""
    cnpj_emit: str = ""
    cnpj_dest: str = ""
    uf_emit: str = ""
    data_emissao: str = "" # AAAAMMDD
    data_entrada: str = "" # AAAAMMDD
    v_bc_icms: Decimal = Decimal("0")
    v_icms: Decimal = Decimal("0")
    v_ipi: Decimal = Decimal("0")
    v_desc: Decimal = Decimal("0")
    v_frete: Decimal = Decimal("0")
    v_seg: Decimal = Decimal("0")
    v_outros: Decimal = Decimal("0")
    v_pis: Decimal = Decimal("0")
    v_cofins: Decimal = Decimal("0")
    items: List[NFeItem] = None