from __future__ import annotations
from formatter import Layout, LayoutField, FieldType


# === ANEXO 07 – Movimento de produtos (Registro C170 – SPED) ===
ANEXO07_C170 = Layout(
    name="ANEXO 07 – C170 (SPED)",
    fields=[
        # 01–20 (do PDF)
        LayoutField("num_item_nf",          FieldType.I),                    # 01 Número do item na NF (I 4)
        LayoutField("c_prod",             FieldType.A, default="S"),       # 02 Código ou Apelido do Produto (A 14)
        LayoutField("tipo_mov",             FieldType.A, default="S"),       # 02 Tipo do Movimento: "E"/"S" (A 1)
        LayoutField("cnpj_cpf_cliente",     FieldType.A, default=""),        # 03 CNPJ/CPF do cliente (A 14/11)
        LayoutField("ie_cliente",           FieldType.I, default=0),         # 05 IE do cliente (I 16)
        LayoutField("num_nf",               FieldType.I, default=0),         # 06 Número da NF (I 9)
        LayoutField("data_nf",              FieldType.A, default=""),        # 07 Data da NF AAAAMMDD (A 8)
        LayoutField("uf_nf",                FieldType.A, default=""),        # 08 UF da NF (A 2)
        LayoutField("serie_nf",             FieldType.A, default=""),        # 09 Série da NF (A 4)
        LayoutField("especie_nf",           FieldType.A, default="NF"),      # 10 Espécie da NF (A 4)
        LayoutField("modelo_nf",            FieldType.N, decimals=0),        # 11 Modelo da NF (N 2)
        LayoutField("qtd_produto",          FieldType.N, decimals=2),        # 12 Quantidade total do produto na NF (N 8.2)
        LayoutField("vl_total_produto",     FieldType.N, decimals=2),        # 13 Valor total do produto (N 14.2)
        LayoutField("aliq_icms",            FieldType.N, decimals=2),        # 14 Alíquota ICMS do produto (N 5.2)
        LayoutField("vl_ipi",               FieldType.N, decimals=2),        # 15 Valor do IPI do produto (N 14.2)
        LayoutField("bc_icms",              FieldType.N, decimals=2),        # 16 Base de cálculo do ICMS do produto (N 14.2)
        LayoutField("bc_st",                FieldType.N, decimals=2),        # 17 Base de cálculo do ST do produto (N 14.2)
        LayoutField("vl_desconto",          FieldType.N, decimals=2),        # 18 Valor desconto do produto (N 14.2)
        LayoutField("nat_oper",             FieldType.A, default=""),        # 19 Código natureza operação (A 7, ex "5102000")
        LayoutField("cst_icms",             FieldType.A, default="000"),     # 20 CST ICMS (A 3)

        # 21–36 (SPED impostos, totalmente legível no PDF)
        LayoutField("mov_fisica_sped",      FieldType.L, default="N"),       # 21 Movimentação física (L 1, "S"/"N")
        LayoutField("cst_cofins_sped",      FieldType.I, default=1),         # 22 CST COFINS (I 2)
        LayoutField("cst_pis_sped",         FieldType.I, default=1),         # 23 CST PIS (I 2)
        LayoutField("cst_ipi_sped",         FieldType.I, default=1),         # 24 CST IPI (I 2)
        LayoutField("aliq_ipi_sped",        FieldType.N, decimals=2),        # 25 Alíquota IPI (N 14.2)
        LayoutField("bc_ipi_sped",          FieldType.N, decimals=2),        # 26 Base Cálculo IPI (N 14.2)
        LayoutField("aliq_pis_sped",        FieldType.N, decimals=2),        # 27 Alíquota PIS (N 14.2)
        LayoutField("bc_pis_sped",          FieldType.N, decimals=2),        # 28 BC PIS (N 14.2)
        LayoutField("vl_pis_sped",          FieldType.N, decimals=2),        # 29 Valor PIS (N 14.2)
        LayoutField("aliq_cofins_sped",     FieldType.N, decimals=2),        # 30 Alíquota COFINS (N 14.2)
        LayoutField("bc_cofins_sped",       FieldType.N, decimals=2),        # 31 BC COFINS (N 14.2)
        LayoutField("vl_cofins_sped",       FieldType.N, decimals=2),        # 32 Valor COFINS (N 14.2)
        LayoutField("vl_icms_sped",         FieldType.N, decimals=2),        # 33 Valor ICMS (SPED) (N 14.2)
        LayoutField("aliq_st_sped",         FieldType.N, decimals=2),        # 34 Alíquota ST (SPED) (N 14.2)
        LayoutField("vl_st_sped",           FieldType.N, decimals=2),        # 35 Valor ST (SPED) (N 14.2)
        LayoutField("conta_analitica_sped", FieldType.A, default=""),        # 36 Código da Conta Analítica (A 20)
        LayoutField("aliq_issqn",           FieldType.N, decimals=2),        # 37 Alíquota ISSQN (N 14.2)
        LayoutField("bc_issqn",             FieldType.N, decimals=2),        # 38 Base ISSQN (N 14.2)
        LayoutField("vl_issqn",             FieldType.N, decimals=2),        # 39 Valor ISSQN (N 14.2)

        # 40–50 (legível)
        LayoutField("classif_item",          FieldType.I, default=0),        # 40 Classificação do item (I 4)
        LayoutField("tipo_receita",          FieldType.N, decimals=0),       # 41 Tipo de receita (N 1)
        LayoutField("desp_acessorias",       FieldType.N, decimals=2),       # 42 Despesas acessórias (N 14.2)
        LayoutField("mun_origem",            FieldType.I, default=0),        # 43 Município origem (I 5)
        LayoutField("mun_destino",           FieldType.I, default=0),        # 44 Município destino (I 5)
        LayoutField("placa",                 FieldType.A, default=""),       # 45 Placa (A 7)
        LayoutField("uf_placa",              FieldType.A, default=""),       # 46 UF Placa (A 2)
        LayoutField("icms_st_repassar",      FieldType.N, decimals=2),       # 47 ICMS-ST a repassar/deduzir (N 14.2)
        LayoutField("icms_st_complementar",  FieldType.N, decimals=2),       # 48 ICMS-ST a completar (N 14.2)
        LayoutField("bc_retencao",           FieldType.N, decimals=2),       # 49 Base de cálculo da retenção (N 14.2)
        LayoutField("parcela_retida",        FieldType.N, decimals=2),       # 50 Parcela do imposto retido (N 14.2)

        # 51–65 (trecho com scan truncado no PDF — tipos/precisão marcados conforme leitura)
        LayoutField("incentivo_fiscal",      FieldType.L, default="N"),      # 51 Incentivo fiscal (L 1) — "S"/"N"
        LayoutField("base_icms_dif_peso",    FieldType.N, decimals=2),       # 52 Base ICMS diferença de peso (N 14.2)
        LayoutField("dif_peso",              FieldType.N, decimals=2),       # 53 Diferença de peso (N 14.2)
        LayoutField("red_base_calc",         FieldType.N, decimals=2),       # 54 Redução da base de cálculo (N 14.2)
        LayoutField("num_di",                FieldType.I, default=0),        # 55 Número da DI (I 10)
        LayoutField("un_med_mov",            FieldType.A, default=""),       # 56 Unidade produto no movimento (A 3)
        LayoutField("cod_selo_ipi",          FieldType.A, default=""),       # 57 Código selo IPI (A 6)
        LayoutField("qtd_selo_ipi",          FieldType.I, default=0),        # 58 Quantidade de selos (I 2)
        LayoutField("classe_ipi_un",         FieldType.A, default=""),       # 59 Classe de tributação por unidade IPI (A 5)
        LayoutField("vl_unit_un_padrao",     FieldType.N, decimals=2),       # 60 Valor unitário por unidade padrão (N 4.2)
        LayoutField("qtd_total_un_padrao",   FieldType.N, decimals=3),       # 61 Quantidade total na unidade padrão (N 14.3)
        LayoutField("cst_simples",           FieldType.A, default=""),       # 62 CST ICMS (Simples Nac.) — tabela descritiva no PDF
        LayoutField("cod_apur_pis_cofins",   FieldType.A, default=""),       # 63 Código apuração PIS/COFINS (texto no PDF)
        LayoutField("saida_incent_prodepe",  FieldType.L, default="N"),      # 64 Saída incentivada Prodepe-PE (L 1)
        LayoutField("perc_prodepe",          FieldType.N, decimals=3),       # 65 Percentual Prodepe-PE (N 14.3)

        # 66–75 (legível)
        LayoutField("vl_frete",              FieldType.N, decimals=2),       # 66 Valor frete (N 9.2)
        LayoutField("vl_seguro",             FieldType.N, decimals=2),       # 67 Valor seguro (N 9.2)
        LayoutField("bc_fcpst",              FieldType.N, decimals=2),       # 68 Base FCP-ST (N 9.2)
        LayoutField("aliq_fcpst",            FieldType.N, decimals=2),       # 69 Alíquota FCP-ST (N 9.2)
        LayoutField("vl_fcpst",              FieldType.N, decimals=2),       # 70 Valor FCP-ST (N 9.2)
        LayoutField("retorno_ipi",           FieldType.N, decimals=2),       # 71 Retorno do IPI (N 9.2)
        LayoutField("bc_fcp_icms",           FieldType.N, decimals=2),       # 72 Base FCP ICMS (N 9.2)
        LayoutField("aliq_fcp_icms",         FieldType.N, decimals=2),       # 73 Alíquota FCP ICMS (N 9.2)
        LayoutField("vl_fcp_icms",           FieldType.N, decimals=2),       # 74 Valor FCP ICMS (N 9.2)
        LayoutField("vl_icms_desonerado",    FieldType.N, decimals=2),       # 75 Valor ICMS desonerado (N 9.2)

        # 76–85 (retido anterior + efetivo)
        LayoutField("bc_icms_st_ret_ant",    FieldType.N, decimals=2),       # 76 Base ICMS ST retido anteriormente (N 14.2)
        LayoutField("aliq_icms_st_ret_ant",  FieldType.N, decimals=2),       # 77 Alíquota ICMS ST retido anteriormente (N 14.2)
        LayoutField("vl_icms_st_ret_ant",    FieldType.N, decimals=2),       # 78 Valor ICMS ST retido anteriormente (N 14.2)
        LayoutField("bc_fcp_st_ret_ant",     FieldType.N, decimals=2),       # 79 Base FCP ST retido anteriormente (N 14.2)
        LayoutField("aliq_fcp_st_ret_ant",   FieldType.N, decimals=2),       # 80 Alíquota FCP ST retido anteriormente (N 14.2)
        LayoutField("vl_fcp_st_ret_ant",     FieldType.N, decimals=2),       # 81 Valor FCP ST retido anteriormente (N 14.2)
        LayoutField("bc_icms_efetivo",       FieldType.N, decimals=2),       # 82 Base ICMS efetivo (N 14.2)
        LayoutField("aliq_icms_efetivo",     FieldType.N, decimals=2),       # 83 Alíquota ICMS efetivo (N 14.2)
        LayoutField("vl_icms_efetivo",       FieldType.N, decimals=2),       # 84 Valor ICMS efetivo (N 14.2)
        LayoutField("red_icms_efetivo",      FieldType.N, decimals=2),       # 85 Redução ICMS efetivo (N 14.2)

        # 86–95 (ST original + Funrural)
        LayoutField("bc_icms_st_original",   FieldType.N, decimals=2),       # 86 Base ICMS ST original (N 14.2)
        LayoutField("aliq_icms_st_original", FieldType.N, decimals=2),       # 87 Alíquota ICMS ST original (N 14.2)
        LayoutField("vl_icms_st_original",   FieldType.N, decimals=2),       # 88 Valor ICMS ST original (N 14.2)
        LayoutField("bc_fcp_st_original",    FieldType.N, decimals=2),       # 89 Base FCP ST original (N 14.2)
        LayoutField("aliq_fcp_st_original",  FieldType.N, decimals=2),       # 90 Alíquota FCP ST original (N 14.2)
        LayoutField("vl_fcp_st_original",    FieldType.N, decimals=2),       # 91 Valor FCP ST original (N 14.2)
        LayoutField("aliq_funrural",         FieldType.N, decimals=2),       # 92 Alíquota Funrural (N 14.2)
        LayoutField("vl_funrural",           FieldType.N, decimals=2),       # 93 Valor Funrural (N 14.2)
        LayoutField("icms_funrural",         FieldType.N, decimals=2),       # 94 ICMS Funrural (N 14.2)
        LayoutField("tipo_funrural",         FieldType.I, default=0),        # 95 Tipo Funrural (I 1)

        # 96–105 (MVA/SN + IPI original)
        LayoutField("vl_mvasn",              FieldType.N, decimals=2),       # 96 Valor MVASN (N 14.2)
        LayoutField("cod_item_giaf",         FieldType.A, default=""),       # 97 Código Item GIAF (A 10)
        LayoutField("vl_diff_base_cred_pres",FieldType.N, decimals=2),       # 98 Valor diferido - Base crédito pres. (N 9.2)
        LayoutField("vl_cred_presumido",     FieldType.N, decimals=2),       # 99 Crédito presumido (N 9.2)
        LayoutField("incent_transporte",     FieldType.L, default="N"),      # 100 Incentivo sobre transporte (L 1)
        LayoutField("base_cred_presumido_imp",FieldType.L, default="N"),     # 101 Base p/ crédito presumido (import.) (L 1)
        LayoutField("saida_entrada_incent",  FieldType.L, default="N"),      # 102 Saída/Entrada incentivada (L 1)
        LayoutField("base_ipi_original",     FieldType.N, decimals=2),       # 103 Base IPI original (N 9.2)
        LayoutField("aliq_ipi_original",     FieldType.N, decimals=2),       # 104 Alíquota IPI original (N 3.2)
        LayoutField("vl_ipi_original",       FieldType.N, decimals=2),       # 105 Valor IPI original (N 9.2)

        # 106–115 (conversões + arrecadação)
        LayoutField("resp_retencao",         FieldType.I, default=0),        # 106 Responsável pela retenção (I 1)
        LayoutField("qtd_convertida",        FieldType.N, decimals=2),       # 107 Quantidade convertida (N 9.2)
        LayoutField("un_convertida",         FieldType.A, default=""),       # 108 Unidade convertida (A 6)
        LayoutField("vl_unit_convertido",    FieldType.N, decimals=2),       # 109 Valor unitário convertido (N 9.2)
        LayoutField("cred_icms_unit_conv",   FieldType.N, decimals=2),       # 110 Crédito ICMS unitário convertido (N 9.2)
        LayoutField("base_st_unit_conv",     FieldType.N, decimals=2),       # 111 Base ST unitária convertida (N 9.2)
        LayoutField("icms_fcp_st_unit_conv", FieldType.N, decimals=2),       # 112 ICMS ST e FCP unitário convertido (N 9.2)
        LayoutField("fcp_st_unit_conv",      FieldType.N, decimals=2),       # 113 FCP ST unitário convertido (N 9.2)
        LayoutField("modelo_arrecadacao",    FieldType.I, default=0),        # 114 Modelo de arrecadação (I 1)
        LayoutField("num_doc_arrecadacao",   FieldType.A, default=""),       # 115 Número documento arrecadação (A 17)

        # 116–133 (Simples Nacional + originais + ST substituído)
        LayoutField("afrmm",                 FieldType.N, decimals=2),       # 116 Adicional Frete Marinha Mercante (N 9.2)
        LayoutField("aliq_cred_sn",          FieldType.N, decimals=2),       # 117 Alíquota Crédito – SN (N 3.2)
        LayoutField("cst_icms_original",     FieldType.A, default=""),       # 118 CST ICMS original da nota (A 4)
        LayoutField("cfop_original",         FieldType.A, default=""),       # 119 CFOP original da nota (A 10)
        LayoutField("base_icms_cred_sn",     FieldType.N, decimals=2),       # 120 Base ICMS Crédito – SN (N 9.2)
        LayoutField("aliq_icms_cred_sn",     FieldType.N, decimals=2),       # 121 Alíquota ICMS Crédito – SN (N 3.2)
        LayoutField("vl_icms_cred_sn",       FieldType.N, decimals=2),       # 122 Valor ICMS Crédito – SN (N 9.2)
        LayoutField("base_icms_original",    FieldType.N, decimals=2),       # 123 Base ICMS original (N 9.2)
        LayoutField("aliq_icms_original",    FieldType.N, decimals=2),       # 124 Alíquota ICMS original (N 3.2)
        LayoutField("vl_icms_original",      FieldType.N, decimals=2),       # 125 Valor ICMS original (N 9.2)
        LayoutField("base_fcp_original",     FieldType.N, decimals=2),       # 126 Base FCP original (N 9.2)
        LayoutField("aliq_fcp_original",     FieldType.N, decimals=2),       # 127 Alíquota FCP original (N 3.2)
        LayoutField("vl_fcp_original",       FieldType.N, decimals=2),       # 128 Valor FCP original (N 9.2)
        LayoutField("origem_mercadoria",     FieldType.I, default=0),        # 129 Origem da mercadoria (I 1)
        LayoutField("modalidade_bc_st",      FieldType.A, default=""),       # 130 Modalidade BC ICMS ST (A 3)
        LayoutField("modalidade_bc_st_orig", FieldType.A, default=""),       # 131 Modalidade BC ICMS ST original (A 3)
        LayoutField("devolucao_valor_item",  FieldType.L, default="N"),      # 132 Devolução do valor do item (L 1)
        LayoutField("vl_st_substituido",     FieldType.N, decimals=2),       # 133 Valor do ST substituído (N 9.2)
    ],
)


# === ANEXO 09 – Entradas (até o campo 52) ===
ANEXO09_ENTRADAS = Layout(
    name="ANEXO 09 – Entradas",
    fields=[
        # 01–27
        LayoutField("chave_import",   FieldType.I, default=1),                     # 01 Número da chave da importação
        LayoutField("cnpj_cpf_cliente", FieldType.A, default=""),                  # 02 CNPJ/CPF/Apelido do fornecedor
        LayoutField("uf_emit",        FieldType.A, default=""),                    # 03 Estado do emitente da nota
        LayoutField("data_entrada",   FieldType.A, default=""),                    # 04 Data da entrada AAAAMMDD
        LayoutField("data_emissao",   FieldType.A, default=""),                    # 05 Data da emissão AAAAMMDD
        LayoutField("num_nf",         FieldType.I, default=0),                     # 06 Número da nota
        LayoutField("especie_doc",    FieldType.A, default="NF"),                  # 07 Espécie do documento
        LayoutField("serie",          FieldType.A, default="1"),                   # 08 Série do documento
        LayoutField("nat_oper",       FieldType.A, default=""),                    # 09 Código natureza operação (ex.: 2102000)
        LayoutField("valor_contabil", FieldType.N, decimals=2, default=0),         # 10 Valor contábil da nota (15.2)
        LayoutField("cst_origem",     FieldType.A, default="0"),                   # 11 CST A: origem (0=nac,1=imp dir,2=estr int)
        LayoutField("cst_icms",       FieldType.A, default="00"),                  # 12 CST B: ICMS (00,10,20,30,40,50,60,70)
        LayoutField("red_bc_icms",    FieldType.N, decimals=4, default=0),         # 13 Redução BC ICMS (8.4)
        LayoutField("bc_icms",        FieldType.N, decimals=2, default=0),         # 14 Base ICMS (15.2)
        LayoutField("aliq_icms",      FieldType.N, decimals=4, default=0),         # 15 Alíquota ICMS (8.4)
        LayoutField("valor_icms",     FieldType.N, decimals=2, default=0),         # 16 Valor ICMS (15.2)
        LayoutField("isentas_icms",   FieldType.N, decimals=2, default=0),         # 17 Isentas ICMS (15.2)
        LayoutField("outras_icms",    FieldType.N, decimals=2, default=0),         # 18 Outras ICMS (15.2)
        LayoutField("icms_st_flag",   FieldType.L, default="N"),                   # 19 ICMS ST – "S"/"N"
        LayoutField("bc_icms_st",     FieldType.N, decimals=2, default=0),         # 20 BC ICMS ST (15.2)
        LayoutField("aliq_icms_st",   FieldType.N, decimals=4, default=0),         # 21 Alíquota ICMS ST (8.4)
        LayoutField("valor_icms_st",  FieldType.N, decimals=2, default=0),         # 22 Valor ICMS ST (14.2 -> usamos 2 casas)
        LayoutField("bc_ipi",         FieldType.N, decimals=2, default=0),         # 23 BC IPI (15.2)
        LayoutField("valor_ipi",      FieldType.N, decimals=2, default=0),         # 24 Valor IPI (15.2)
        LayoutField("isentas_ipi",    FieldType.N, decimals=2, default=0),         # 25 Isentas IPI (15.2)
        LayoutField("outras_ipi",     FieldType.N, decimals=2, default=0),         # 26 Outras IPI (15.2)
        LayoutField("observacao",     FieldType.A, default=""),                    # 27 Observação (A 90)

        # 28–52: múltiplas alíquotas de ICMS (até 5 faixas)
        LayoutField("bc_icms_1",      FieldType.N, decimals=2, default=0),         # 28 Base ICMS 1 (15.2)
        LayoutField("bc_icms_2",      FieldType.N, decimals=2, default=0),         # 29 Base ICMS 2 (15.2)
        LayoutField("bc_icms_3",      FieldType.N, decimals=2, default=0),         # 30 Base ICMS 3 (15.2)
        LayoutField("bc_icms_4",      FieldType.N, decimals=2, default=0),         # 31 Base ICMS 4 (15.2)
        LayoutField("bc_icms_5",      FieldType.N, decimals=2, default=0),         # 32 Base ICMS 5 (15.2)
        LayoutField("aliq_icms_1",    FieldType.N, decimals=2, default=0),         # 33 Alíquota ICMS 1 (5.2)
        LayoutField("aliq_icms_2",    FieldType.N, decimals=2, default=0),         # 34 Alíquota ICMS 2 (5.2)
        LayoutField("aliq_icms_3",    FieldType.N, decimals=2, default=0),         # 35 Alíquota ICMS 3 (5.2)
        LayoutField("aliq_icms_4",    FieldType.N, decimals=2, default=0),         # 36 Alíquota ICMS 4 (5.2)
        LayoutField("aliq_icms_5",    FieldType.N, decimals=2, default=0),         # 37 Alíquota ICMS 5 (5.2)
        LayoutField("valor_icms_1",   FieldType.N, decimals=2, default=0),         # 38 Valor ICMS 1 (15.2)
        LayoutField("valor_icms_2",   FieldType.N, decimals=2, default=0),         # 39 Valor ICMS 2 (15.2)
        LayoutField("valor_icms_3",   FieldType.N, decimals=2, default=0),         # 40 Valor ICMS 3 (15.2)
        LayoutField("valor_icms_4",   FieldType.N, decimals=2, default=0),         # 41 Valor ICMS 4 (15.2)
        LayoutField("valor_icms_5",   FieldType.N, decimals=2, default=0),         # 42 Valor ICMS 5 (15.2)
        LayoutField("valor_base_icms_1", FieldType.N, decimals=2, default=0),      # 43 Valor da base ICMS 1 (15.2)
        LayoutField("valor_base_icms_2", FieldType.N, decimals=2, default=0),      # 44 Valor da base ICMS 2 (15.2)
        LayoutField("valor_base_icms_3", FieldType.N, decimals=2, default=0),      # 45 Valor da base ICMS 3 (15.2)
        LayoutField("valor_base_icms_4", FieldType.N, decimals=2, default=0),      # 46 Valor da base ICMS 4 (15.2)
        LayoutField("valor_base_icms_5", FieldType.N, decimals=2, default=0),      # 47 Valor da base ICMS 5 (15.2)
        LayoutField("perc_red_base_1", FieldType.N, decimals=2, default=0),        # 48 % redução BC 1 (5.2)
        LayoutField("perc_red_base_2", FieldType.N, decimals=2, default=0),        # 49 % redução BC 2 (5.2)
        LayoutField("perc_red_base_3", FieldType.N, decimals=2, default=0),        # 50 % redução BC 3 (5.2)
        LayoutField("perc_red_base_4", FieldType.N, decimals=2, default=0),        # 51 % redução BC 4 (5.2)
        LayoutField("perc_red_base_5", FieldType.N, decimals=2, default=0),        # 52 % redução BC 5 (5.2)
    ],
)

# === ANEXO 04 – Saídas (até o campo 31) ===
ANEXO04_SAIDAS = Layout(
    name="ANEXO 04 – Saídas",
    fields=[
        # 01 a 31 conforme PDF "Movimento de saídas"
        LayoutField("chave_import", FieldType.I, default=1),                 # 01 Número da chave da importação
        LayoutField("cnpj_cpf_cliente", FieldType.A, default=""),          # 02 CNPJ/CPF/Apelido cliente
        LayoutField("uf_dest", FieldType.A, default=""),                   # 03 UF do destinatário
        LayoutField("data_emissao", FieldType.A, default=""),              # 04 Data emissão AAAAMMDD
        LayoutField("num_nf_ini", FieldType.I, default=0),                  # 05 Número inicial
        LayoutField("num_nf_fim", FieldType.I, default=0),                  # 06 Número final (repete se única NF)
        LayoutField("especie_doc", FieldType.A, default="NF"),             # 07 Espécie do documento
        LayoutField("serie", FieldType.A, default="1"),                    # 08 Série do documento
        LayoutField("nat_oper", FieldType.A, default=""),                  # 09 Código natureza operação (ex.: 5102000)
        LayoutField("valor_contabil", FieldType.N, decimals=2, default=0),  # 10 Valor contábil da nota
        LayoutField("reservado_11", FieldType.A, default="0"),             # 11 Reservado – fixo "0"
        LayoutField("reservado_12", FieldType.A, default="0"),             # 12 Reservado – fixo "0"
        LayoutField("red_bc_icms", FieldType.N, decimals=2, default=0),     # 13 Redução da BC ICMS
        LayoutField("bc_icms", FieldType.N, decimals=2, default=0),         # 14 Base de cálculo ICMS (soma das BCs)
        LayoutField("aliq_icms", FieldType.N, decimals=2, default=0),       # 15 Alíquota ICMS (soma ou principal)
        LayoutField("valor_icms", FieldType.N, decimals=2, default=0),      # 16 Valor ICMS (soma)
        LayoutField("isentas_icms", FieldType.N, decimals=2, default=0),    # 17 Isentas ICMS
        LayoutField("outras_icms", FieldType.N, decimals=2, default=0),     # 18 Outras ICMS
        LayoutField("icms_st_flag", FieldType.L, default="N"),             # 19 ICMS substituição – "S"/"N"
        LayoutField("bc_icms_st", FieldType.N, decimals=2, default=0),      # 20 Base de cálculo ICMS ST
        LayoutField("aliq_icms_st", FieldType.N, decimals=2, default=0),    # 21 Alíquota ICMS ST
        LayoutField("valor_icms_st", FieldType.N, decimals=2, default=0),   # 22 Valor ICMS ST
        LayoutField("bc_ipi", FieldType.N, decimals=2, default=0),          # 23 Base de cálculo IPI
        LayoutField("valor_ipi", FieldType.N, decimals=2, default=0),       # 24 Valor do IPI
        LayoutField("isentas_ipi", FieldType.N, decimals=2, default=0),     # 25 Isentas IPI
        LayoutField("outras_ipi", FieldType.N, decimals=2, default=0),      # 26 Outras IPI
        LayoutField("cesta_basica_flag", FieldType.L, default="N"),        # 27 Cesta básica – "S"/"N"
        LayoutField("bc_cesta", FieldType.N, decimals=2, default=0),        # 28 Base de cálculo cesta básica
        LayoutField("aliq_cesta", FieldType.N, decimals=2, default=0),      # 29 Alíquota cesta básica
        LayoutField("valor_cesta", FieldType.N, decimals=2, default=0),     # 30 Valor cesta básica
        LayoutField("observacao", FieldType.A, default=""),                # 31 Observação
    ],
)

