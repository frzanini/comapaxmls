from __future__ import annotations
from decimal import Decimal as D
from typing import Dict, Any, List, Tuple
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
# --- helper: agrupa até 5 faixas de ICMS por alíquota ---
def _split_icms_faixas(nota: NFeNota) -> List[Tuple[D, D, D]]:
    """
    Retorna lista de (bc, aliq, valor) agrupada por alíquota (p_icms).
    Até 5 faixas; excedentes são ignoradas.
    """
    buckets: Dict[str, Tuple[D, D, D]] = {}
    for it in (nota.items or []):
        aliq = D(str(it.p_icms or 0))
        bc = D(str(it.v_bc_icms or 0))
        vicms = D(str(it.v_icms or 0))
        key = str(aliq)
        if key not in buckets:
            buckets[key] = (D("0"), aliq, D("0"))
        b_bc, b_aliq, b_val = buckets[key]
        buckets[key] = (b_bc + bc, aliq, b_val + vicms)
    # ordena por alíquota desc e pega no máximo 5
    return sorted(buckets.values(), key=lambda t: t[1], reverse=True)[:5]

# --- Anexo 09 (Entradas) ---
def map_nota_to_entradas(nota: NFeNota, chave_import: int) -> Dict[str, Any]:
    total_produtos = sum((i.v_prod for i in (nota.items or [])), start=D("0"))
    total_bc_st    = sum((i.v_bc_st for i in (nota.items or [])), start=D("0"))
    total_icms_st  = sum((i.v_icms_st for i in (nota.items or [])), start=D("0"))

    cst_item0  = (nota.items[0].cst_icms if nota.items else "00")
    aliq_item0 = (nota.items[0].p_icms if nota.items else D("0"))
    tem_st     = any((i.v_icms_st or 0) > 0 for i in (nota.items or []))

    cst_origem = "0"  # default seguro (nacional) quando não vier do domínio

    # 28–52: faixas por alíquota
    faixas = _split_icms_faixas(nota)
    def _get(i, idx):
        try:
            return faixas[idx][i]
        except IndexError:
            return D("0")

    row: Dict[str, Any] = {
        # 01–10
        "chave_import": int(chave_import),
        "cnpj_cpf_cliente": nota.cnpj_emit or nota.cnpj_dest or "",  # fornecedor
        "uf_emit":       nota.uf_emit or "",
        "data_entrada":  nota.data_entrada or "",
        "data_emissao":  nota.data_emissao or "",
        "num_nf":        int(nota.numero or 0),
        "especie_doc":   "NF",
        "serie":         nota.serie or "1",
        "nat_oper":      (nota.items[0].cfop if nota.items else ""),
        "valor_contabil": total_produtos,
        # 11–18
        "cst_origem":    cst_origem,
        "cst_icms":      cst_item0,
        "red_bc_icms":   D("0"),
        "bc_icms":       nota.v_bc_icms,
        "aliq_icms":     aliq_item0,
        "valor_icms":    nota.v_icms,
        "isentas_icms":  D("0"),
        "outras_icms":   D("0"),
        # 19–22 (ST)
        "icms_st_flag":  "S" if tem_st else "N",
        "bc_icms_st":    total_bc_st,
        "aliq_icms_st":  D("0"),
        "valor_icms_st": total_icms_st,
        # 23–27 (IPI/obs)
        "bc_ipi":        D("0"),
        "valor_ipi":     nota.v_ipi,
        "isentas_ipi":   D("0"),
        "outras_ipi":    D("0"),
        "observacao":    "",
        # 28–52 – faixas ICMS 1..5
        "bc_icms_1": _get(0, 0), "bc_icms_2": _get(0, 1), "bc_icms_3": _get(0, 2), "bc_icms_4": _get(0, 3), "bc_icms_5": _get(0, 4),
        "aliq_icms_1": _get(1, 0), "aliq_icms_2": _get(1, 1), "aliq_icms_3": _get(1, 2), "aliq_icms_4": _get(1, 3), "aliq_icms_5": _get(1, 4),
        "valor_icms_1": _get(2, 0), "valor_icms_2": _get(2, 1), "valor_icms_3": _get(2, 2), "valor_icms_4": _get(2, 3), "valor_icms_5": _get(2, 4),
        "valor_base_icms_1": _get(0, 0), "valor_base_icms_2": _get(0, 1), "valor_base_icms_3": _get(0, 2), "valor_base_icms_4": _get(0, 3), "valor_base_icms_5": _get(0, 4),
        "perc_red_base_1": D("0"), "perc_red_base_2": D("0"), "perc_red_base_3": D("0"), "perc_red_base_4": D("0"), "perc_red_base_5": D("0"),
    }
    return row



# --- Anexo 04 (Saídas) ---
def map_nota_to_saidas(nota: NFeNota, chave_import: int) -> Dict[str, Any]:
    # Soma úteis
    total_produtos = sum((i.v_prod for i in (nota.items or [])), start=D("0"))
    total_bc_st = sum((i.v_bc_st for i in (nota.items or [])), start=D("0"))
    total_icms_st = sum((i.v_icms_st for i in (nota.items or [])), start=D("0"))

    # Heurísticas quando informação não existir no domínio
    cst_item0 = nota.items[0].cst_icms if nota.items else "00"
    aliq_item0 = nota.items[0].p_icms if nota.items else D("0")
    tem_st = any((i.v_icms_st or 0) > 0 for i in (nota.items or []))

    return {
        # 01–06
        "chave_import": int(chave_import),
        "cnpj_cpf_cliente": nota.cnpj_dest or nota.cnpj_emit or "",
        "uf_dest": nota.uf_emit or "",              # TODO: ajustar para UF do destinatário quando disponível no parser
        "data_emissao": nota.data_emissao or "",    # AAAAMMDD
        "num_nf_ini": int(nota.numero or 0),
        "num_nf_fim": int(nota.numero or 0),
        # 07–10
        "especie_doc": "NF",
        "serie": nota.serie or "1",
        "nat_oper": (nota.items[0].cfop if nota.items else ""),  # código natureza (ex.: 5102000)
        "valor_contabil": total_produtos,
        # 11–18
        "reservado_11": "0",
        "reservado_12": "0",
        "red_bc_icms": D("0"),
        "bc_icms": nota.v_bc_icms,
        "aliq_icms": aliq_item0,
        "valor_icms": nota.v_icms,
        "isentas_icms": D("0"),
        "outras_icms": D("0"),
        # 19–22 (ST)
        "icms_st_flag": "S" if tem_st else "N",
        "bc_icms_st": total_bc_st,
        "aliq_icms_st": D("0"),
        "valor_icms_st": total_icms_st,
        # 23–26 (IPI)
        "bc_ipi": D("0"),
        "valor_ipi": nota.v_ipi,
        "isentas_ipi": D("0"),
        "outras_ipi": D("0"),
        # 27–31 (cesta/obs)
        "cesta_basica_flag": "N",
        "bc_cesta": D("0"),
        "aliq_cesta": D("0"),
        "valor_cesta": D("0"),
        "observacao": "",
    }



