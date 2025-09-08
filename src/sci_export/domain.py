from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Dict


@dataclass
class NFeItem:
    # Básicos (C170 + necessidades Anexo 04/09)
    n_item: int
    c_prod: str = ""
    cfop: str = ""
    u_com: str = ""
    q_com: Decimal = Decimal("0")
    v_un_com: Decimal = Decimal("0")
    v_prod: Decimal = Decimal("0")

    # ICMS / ST
    cst_icms: str = ""                # CST/CSOSN
    p_icms: Decimal = Decimal("0")
    v_bc_icms: Decimal = Decimal("0")
    v_icms: Decimal = Decimal("0")

    v_bc_st: Decimal = Decimal("0")
    p_icms_st: Decimal = Decimal("0")
    v_icms_st: Decimal = Decimal("0")

    # IPI
    p_ipi: Decimal = Decimal("0")
    v_ipi: Decimal = Decimal("0")

    # PIS/COFINS
    p_pis: Decimal = Decimal("0")
    v_pis: Decimal = Decimal("0")
    p_cofins: Decimal = Decimal("0")
    v_cofins: Decimal = Decimal("0")

    # Campos auxiliares para C170/Sped e layouts (quando existirem no XML)
    cst_pis: str = ""
    cst_cofins: str = ""
    cst_ipi: str = ""                 # ex.: 50, 99 (quando aplicável)
    aliq_st_sped: Decimal = Decimal("0")   # “Aliquota do ST (Sped)”
    conta_analitica_sped: str = ""    # “Código da Conta Analítica (Sped)”
    despesas_acessorias: Decimal = Decimal("0")
    icms_st_deduzir: Decimal = Decimal("0")
    icms_st_completar: Decimal = Decimal("0")
    base_retencao: Decimal = Decimal("0")
    parcela_imposto_retido: Decimal = Decimal("0")
    # Funrural / FCP / efetivo (novas tags modernas quando disponíveis)
    aliq_funrural: Decimal = Decimal("0")
    v_funrural: Decimal = Decimal("0")
    icms_funrural: Decimal = Decimal("0")
    base_fcp_st: Decimal = Decimal("0")
    p_fcp_st: Decimal = Decimal("0")
    v_fcp_st: Decimal = Decimal("0")
    base_fcp: Decimal = Decimal("0")
    p_fcp: Decimal = Decimal("0")
    v_fcp: Decimal = Decimal("0")
    # Campos de conversão/unidade alternativa (C170 final)
    qtd_convertida: Decimal = Decimal("0")
    unid_convertida: str = ""
    v_unit_convertido: Decimal = Decimal("0")
    credito_icms_unit_convertido: Decimal = Decimal("0")
    base_st_unit_convertida: Decimal = Decimal("0")
    icms_st_fcp_unit_convertido: Decimal = Decimal("0")
    fcp_st_unit_convertido: Decimal = Decimal("0")


@dataclass
class NFeNota:
    # Identificação
    chave: str = ""
    modelo: str = "55"
    serie: str = ""
    numero: str = ""
    # Partes
    cnpj_emit: str = ""
    cnpj_dest: str = ""
    uf_emit: str = ""
    uf_dest: str = ""
    ie_emit: str = ""  # Inscrição Estadual do emitente (pode ser "ISENTO")
    ie_dest: str = ""  # Inscrição Estadual do destinatário (pode ser "ISENTO")
    
    # Datas AAAAMMDD
    data_emissao: str = ""
    data_entrada: str = ""
    # Totais (nota)
    v_bc_icms: Decimal = Decimal("0")
    v_icms: Decimal = Decimal("0")
    v_ipi: Decimal = Decimal("0")
    v_desc: Decimal = Decimal("0")
    v_frete: Decimal = Decimal("0")
    v_seg: Decimal = Decimal("0")
    v_outros: Decimal = Decimal("0")
    v_pis: Decimal = Decimal("0")
    v_cofins: Decimal = Decimal("0")

    # Campos de cabeçalho úteis aos anexos 04/09
    especie: str = "NF"               # Ex.: "NF" (espécie do doc)
    serie_doc: str = ""               # redundância de série quando necessário
    modelo_doc: str = ""              # redundância de modelo quando necessário
    nat_oper: str = ""                # natOp textual da NFe
    # Indicadores
    ind_final: Optional[int] = None   # consumidor final (0/1)
    ind_pres: Optional[int] = None    # presença (0..9)
    # CFOP(s) presentes na nota (para decidir naturezas)
    cfops: List[str] = field(default_factory=list)

    # Quebra por alíquotas (opcional) — úteis se quiser preencher campos 28..52 (variantes)
    # Chaves: aliquota (str/Decimal) -> dict(base, icms, red_pct)
    icms_por_aliquota: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)

    # Documentos de transporte/CT-e relacionados (Sped)
    chaves_cte: List[str] = field(default_factory=list)

    # Veículos (GRF) e frete
    frete_modalidade: Optional[int] = None  # 0/1/2/9 etc. conforme SPED
    placa1: str = ""
    uf_placa1: str = ""
    placa2: str = ""
    uf_placa2: str = ""
    placa3: str = ""
    uf_placa3: str = ""
    valor_frete_doc: Decimal = Decimal("0")

    # Importação (DI) simplificada
    di_numero: str = ""
    di_moeda: Optional[int] = None  # 0 dólar, 1 euro (quando aplicável)
    di_valor_brl: Decimal = Decimal("0")
    di_valor_moeda: Decimal = Decimal("0")

    # Observação da nota
    observacao: str = ""

    # Itens
    items: List[NFeItem] = field(default_factory=list)

    # Apoio (para decidir se é entrada/saída externamente)
    def is_saida(self, who_cnpj: str) -> bool:
        return (self.cnpj_emit == who_cnpj) if who_cnpj else False

    def is_entrada(self, who_cnpj: str) -> bool:
        return (self.cnpj_dest == who_cnpj) if who_cnpj else False
