from __future__ import annotations
from formatter import Layout, LayoutField, FieldType

ANEXO07_C170 = Layout(
    name="ANEXO 07 – C170 (Produtos)",
    fields=[
        LayoutField("num_item_nf", FieldType.I, default=0),
        LayoutField("cod_prod", FieldType.A, default=""),
        LayoutField("tipo_mov", FieldType.A, default="E"),
        LayoutField("cnpj_cpf_cliente", FieldType.A, default=""),
        LayoutField("ie_cliente", FieldType.I, default=0),
        LayoutField("num_nf", FieldType.I, default=0),
        LayoutField("data_nf", FieldType.A, default=""),
        LayoutField("uf_nf", FieldType.A, default=""),
        LayoutField("serie_nf", FieldType.A, default="1"),
        LayoutField("especie_nf", FieldType.A, default="NF"),
        LayoutField("modelo_nf", FieldType.I, default=55),
        LayoutField("qtd_total_item", FieldType.N, decimals=2, default=0),
        LayoutField("valor_total_item", FieldType.N, decimals=2, default=0),
        LayoutField("aliq_icms", FieldType.N, decimals=2, default=0),
        LayoutField("valor_ipi", FieldType.N, decimals=2, default=0),
        LayoutField("bc_icms", FieldType.N, decimals=2, default=0),
        LayoutField("bc_st", FieldType.N, decimals=2, default=0),
        LayoutField("valor_desc", FieldType.N, decimals=2, default=0),
        LayoutField("cfop", FieldType.A, default=""),
        LayoutField("cst_icms", FieldType.A, default=""),
        LayoutField("mov_fisica", FieldType.L, default=True),
        LayoutField("cst_cofins", FieldType.I, default=1),
        LayoutField("cst_pis", FieldType.I, default=1),
        LayoutField("cst_ipi", FieldType.I, default=1),
        LayoutField("aliq_ipi", FieldType.N, decimals=2, default=0),
        LayoutField("bc_ipi", FieldType.N, decimals=2, default=0),
        LayoutField("aliq_pis", FieldType.N, decimals=2, default=0),
        LayoutField("bc_pis", FieldType.N, decimals=2, default=0),
        LayoutField("valor_pis", FieldType.N, decimals=2, default=0),
        LayoutField("aliq_cofins", FieldType.N, decimals=2, default=0),
        LayoutField("bc_cofins", FieldType.N, decimals=2, default=0),
        LayoutField("valor_cofins", FieldType.N, decimals=2, default=0),
        LayoutField("valor_icms", FieldType.N, decimals=2, default=0),
        LayoutField("aliq_st", FieldType.N, decimals=2, default=0),
        LayoutField("valor_st", FieldType.N, decimals=2, default=0),
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

