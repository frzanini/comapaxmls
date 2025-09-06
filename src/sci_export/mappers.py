from __future__ import annotations
from decimal import Decimal
from typing import Dict, Any
from domain import NFeNota, NFeItem

# --- Anexo 07 (C170) ---
def map_item_to_c170(nota: NFeNota, item: NFeItem, tipo_mov: str) -> Dict[str, Any]:
    return {
        "num_item_nf": item.n_item,
        "cod_prod": item.c_prod,
        "tipo_mov": tipo_mov,  # "E"/"S"
        "cnpj_cpf_cliente": nota.cnpj_dest or nota.cnpj_emit,
        "ie_cliente": 0,
        "num_nf": int(nota.numero or 0),
        "data_nf": nota.data_emissao,
        "uf_nf": nota.uf_emit,
        "serie_nf": nota.serie or "1",
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

# --- Anexo 09 (Entradas) ---
def map_nota_to_entradas(nota: NFeNota, seq: int) -> Dict[str, Any]:
    cfop = nota.items[0].cfop if nota.items else ""
    from decimal import Decimal as D
    return {
        "chave_import": seq,
        "cnpj_cpf_cliente": nota.cnpj_emit,  # fornecedor/emitente
        "uf_emit": nota.uf_emit,
        "data_entrada": nota.data_entrada,
        "data_emissao": nota.data_emissao,
        "num_nf": int(nota.numero or 0),
        "especie_doc": "NF",
        "serie": nota.serie or "1",
        "nat_oper": cfop or "",
        "valor_contabil": sum((i.v_prod for i in (nota.items or [])), start=D("0")),
        "origem_merc": "0",
        "cst_icms": (nota.items[0].cst_icms if nota.items else "00"),
        "red_bc_icms": D("0"),
        "bc_icms": nota.v_bc_icms,
        "aliq_icms": (nota.items[0].p_icms if nota.items else D("0")),
        "valor_icms": nota.v_icms,
        "isentas_icms": D("0"),
        "outras_icms": D("0"),
        "icms_st_flag": "S" if any((i.v_icms_st or 0) > 0 for i in (nota.items or [])) else "N",
        "bc_icms_st": sum((i.v_bc_st for i in (nota.items or [])), start=D("0")),
        "aliq_icms_st": (nota.items[0].p_icms_st if nota.items else D("0")),
        "valor_icms_st": sum((i.v_icms_st for i in (nota.items or [])), start=D("0")),
        "bc_ipi": D("0"),
        "valor_ipi": nota.v_ipi,
    }

# --- Anexo 04 (Saídas) ---
def map_nota_to_saidas(nota: NFeNota, seq: int) -> Dict[str, Any]:
    cfop = nota.items[0].cfop if nota.items else ""
    return {
        "chave_import": seq,
        "cnpj_cpf_cliente": nota.cnpj_dest,  # destinatário
        "uf_emit": nota.uf_emit,
        "data_saida": nota.data_entrada or nota.data_emissao,
        "data_emissao": nota.data_emissao,
        "num_nf": int(nota.numero or 0),
        "especie_doc": "NF",
        "serie": nota.serie or "1",
        "nat_oper": cfop or "",
        "valor_contabil": sum((i.v_prod for i in (nota.items or [])), start=Decimal("0")),
        "cst_icms": (nota.items[0].cst_icms if nota.items else "00"),
        "bc_icms": nota.v_bc_icms,
        "aliq_icms": (nota.items[0].p_icms if nota.items else Decimal("0")),
        "valor_icms": nota.v_icms,
        "valor_ipi": nota.v_ipi,
        "valor_frete": nota.v_frete,
        "valor_seg": nota.v_seg,
        "valor_outras": nota.v_outros,
    }