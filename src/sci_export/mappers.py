from __future__ import annotations
from decimal import Decimal as D
from typing import Dict, Any, List, Tuple
from domain import NFeNota, NFeItem



def map_item_to_c170(nota: NFeNota, item: NFeItem, tipo_mov: str) -> Dict[str, Any]:
    """
    Mapeia um item de NF-e para o layout C170 (Anexo 07).
    Retorna dict com as chaves exatamente iguais às do layout SCI.
    """
    is_saida = (str(tipo_mov or "S").upper() == "S")
    cnpj_cli = (nota.cnpj_dest if is_saida else nota.cnpj_emit) or ""
    ie_cli   = (nota.ie_dest if is_saida else getattr(nota, "ie_emit", "")) or ""

    # Helpers
    def nz(v, casas=2):
        try:
            return round(D(str(v or "0")), casas)
        except Exception:
            return D("0")

    row: Dict[str, Any] = {
        # 01–20 núcleo
        "num_item_nf":      int(getattr(item, "n_item", 1)),
        "c_prod":           getattr(item, "c_prod", ""),
        "tipo_mov":         ("S" if is_saida else "E"),
        "cnpj_cpf_cliente": cnpj_cli,
        "ie_cliente":       ie_cli,
        "num_nf":           int(nota.numero or 0),
        "data_nf":          nota.data_emissao or "",
        "uf_nf":            nota.uf_emit or "",
        "serie_nf":         nota.serie or "",
        "especie_nf":       nota.especie or "NFF",
        "modelo_nf":        nota.modelo or "55",
        "qtd_produto":      nz(item.q_com),
        "vl_total_produto": nz(item.v_prod),
        "aliq_icms":        nz(item.p_icms),
        "vl_ipi":           nz(item.v_ipi),
        "bc_icms":          nz(item.v_bc_icms),
        "bc_st":            nz(item.v_bc_st),
        "vl_desconto":      nz(getattr(item, "v_desc", 0)),
        "nat_oper":         item.cfop or "",
        "cst_icms":         item.cst_icms or "",

        # 21–36 SPED
        "mov_fisica":       "S",  # default Sim
        "cst_cofins":       getattr(item, "cst_cofins", "01"),
        "cst_pis":          getattr(item, "cst_pis", "01"),
        "cst_ipi":          getattr(item, "cst_ipi", "01"),
        "aliq_ipi":         nz(item.p_ipi),
        "bc_ipi":           nz(getattr(item, "v_bc_ipi", 0)),
        "aliq_pis":         nz(item.p_pis),
        "bc_pis":           nz(getattr(item, "v_bc_pis", 0)),
        "vl_pis":           nz(item.v_pis),
        "aliq_cofins":      nz(item.p_cofins),
        "bc_cofins":        nz(getattr(item, "v_bc_cofins", 0)),
        "vl_cofins":        nz(item.v_cofins),
        "vl_icms":          nz(item.v_icms),
        "aliq_st":          nz(getattr(item, "aliq_st_sped", 0)),
        "vl_st":            nz(item.v_icms_st),
        "conta_analitica":  getattr(item, "conta_analitica_sped", ""),
        "aliq_issqn":       D("0.00"),
        "bc_issqn":         D("0.00"),
        "vl_issqn":         D("0.00"),

        # 40–50 logística/ST retenção
        "classif_item":     getattr(item, "classif_item", 0),
        "tipo_receita":     getattr(item, "tipo_receita", 0),
        "desp_acessorias":  nz(getattr(item, "despesas_acessorias", 0)),
        "mun_origem":       getattr(item, "mun_origem", "00000"),
        "mun_destino":      getattr(item, "mun_destino", "00000"),
        "placa":            getattr(nota, "placa1", ""),
        "uf_placa":         getattr(nota, "uf_placa1", ""),
        "icms_st_repassar": nz(getattr(item, "icms_st_deduzir", 0)),
        "icms_st_completar":nz(getattr(item, "icms_st_completar", 0)),
        "bc_retencao":      nz(getattr(item, "base_retencao", 0)),
        "parcela_retida":   nz(getattr(item, "parcela_imposto_retido", 0)),

        # 51–65 (incentivo, DI, conversões etc.)
        "incentivo_fiscal": "N",
        "base_icms_dif_peso": D("0.00"),
        "dif_peso":         D("0.00"),
        "red_base_calc":    D("0.00"),
        "num_di":           "",
        "un_med_mov":       getattr(item, "u_com", ""),
        "cod_selo_ipi":     "",
        "qtd_selo_ipi":     0,
        "classe_ipi_un":    "",
        "vl_unit_un_padrao": nz(item.v_un_com),
        "qtd_total_un_padrao": nz(item.q_com),
        "cst_simples":      "",
        "cod_apur_pis_cofins": "",
        "saida_incent_prodepe": "N",
        "perc_prodepe":     D("0.00"),

        # 66–133 (frete, FCP, efetivo, originais, conversões etc.)
        "vl_frete":         nz(getattr(item, "v_frete", 0)),
        "vl_seguro":        nz(getattr(item, "v_seg", 0)),
        "bc_fcpst":         nz(getattr(item, "base_fcp_st", 0)),
        "aliq_fcpst":       nz(getattr(item, "p_fcp_st", 0)),
        "vl_fcpst":         nz(getattr(item, "v_fcp_st", 0)),
        "retorno_ipi":      D("0.00"),
        "bc_fcp_icms":      nz(getattr(item, "base_fcp", 0)),
        "aliq_fcp_icms":    nz(getattr(item, "p_fcp", 0)),
        "vl_fcp_icms":      nz(getattr(item, "v_fcp", 0)),
        "vl_icms_desonerado": D("0.00"),
        "bc_icms_st_ret_ant": D("0.00"),
        "aliq_icms_st_ret_ant": D("0.00"),
        "vl_icms_st_ret_ant": D("0.00"),
        "bc_fcp_st_ret_ant": D("0.00"),
        "aliq_fcp_st_ret_ant": D("0.00"),
        "vl_fcp_st_ret_ant": D("0.00"),
        "bc_icms_efetivo":  D("0.00"),
        "aliq_icms_efetivo": D("0.00"),
        "vl_icms_efetivo":  D("0.00"),
        "red_icms_efetivo": D("0.00"),
        "bc_icms_st_original": D("0.00"),
        "aliq_icms_st_original": D("0.00"),
        "vl_icms_st_original": D("0.00"),
        "bc_fcp_st_original": D("0.00"),
        "aliq_fcp_st_original": D("0.00"),
        "vl_fcp_st_original": D("0.00"),
        "aliq_funrural":    D("0.00"),
        "vl_funrural":      D("0.00"),
        "icms_funrural":    D("0.00"),
        "tipo_funrural":    0,
        "vl_mvasn":         D("0.00"),
        "cod_item_giaf":    "",
        "vl_diff_base_cred_pres": D("0.00"),
        "vl_cred_presumido":D("0.00"),
        "incent_transporte": "N",
        "base_cred_presumido_imp": "N",
        "saida_entrada_incent": "N",
        "base_ipi_original": D("0.00"),
        "aliq_ipi_original": D("0.00"),
        "vl_ipi_original":  D("0.00"),
        "resp_retencao":    0,
        "qtd_convertida":   D("0.00"),
        "un_convertida":    "",
        "vl_unit_convertido": D("0.00"),
        "cred_icms_unit_conv": D("0.00"),
        "base_st_unit_conv": D("0.00"),
        "icms_fcp_st_unit_conv": D("0.00"),
        "fcp_st_unit_conv": D("0.00"),
        "modelo_arrecadacao": 0,
        "num_doc_arrecadacao": "",
        "afrmm":            D("0.00"),
        "aliq_cred_sn":     D("0.00"),
        "cst_icms_original": "",
        "cfop_original":   "",
        "base_icms_cred_sn": D("0.00"),
        "aliq_icms_cred_sn": D("0.00"),
        "vl_icms_cred_sn": D("0.00"),
        "base_icms_original": D("0.00"),
        "aliq_icms_original": D("0.00"),
        "vl_icms_original": D("0.00"),
        "base_fcp_original": D("0.00"),
        "aliq_fcp_original": D("0.00"),
        "vl_fcp_original": D("0.00"),
        "origem_mercadoria": 0,
        "modalidade_bc_st": "",
        "modalidade_bc_st_orig": "",
        "devolucao_valor_item": "N",
        "vl_st_substituido": D("0.00"),
    }

    return row

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



