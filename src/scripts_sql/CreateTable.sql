-- Certifica que o schema 'bronze' existe
CREATE SCHEMA IF NOT EXISTS bronze;

-- Tabela principal de identificação de DF-e (NF-e, CT-e, MDF-e, etc.)
CREATE TABLE IF NOT EXISTS bronze.identificacao_dfe (
    sk SERIAL PRIMARY KEY,
    cnpjcpf_emitente VARCHAR(14),
    cnpjcpf_destinatario VARCHAR(14),
    data_emissao TIMESTAMP,
    chave_acesso VARCHAR(60) UNIQUE NOT NULL,
    tipo_documento VARCHAR(20),
    endereco_s3 TEXT,
    data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de eventos vinculados a documentos fiscais
CREATE TABLE IF NOT EXISTS bronze.evento_dfe (
    sk_evento SERIAL PRIMARY KEY,
    chave_acesso VARCHAR(60) UNIQUE NOT NULL, -- mesma da nota referida
    tipo_evento VARCHAR(20),
    descricao_evento TEXT,
    data_evento TIMESTAMP,
    protocolo TEXT,
    cnpjcpf_emitente VARCHAR(14),
    endereco_s3 TEXT,
    data_processamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_identificacao_dfe_data ON bronze.identificacao_dfe(data_emissao);
CREATE INDEX IF NOT EXISTS idx_evento_dfe_tipo ON bronze.evento_dfe(tipo_evento);

-- Remova a constraint antiga se existir:
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'evento_dfe_chave_acesso_key'
      AND conrelid = 'bronze.evento_dfe'::regclass
  ) THEN
    ALTER TABLE bronze.evento_dfe DROP CONSTRAINT evento_dfe_chave_acesso_key;
  END IF;
END$$;

-- Garanta a unicidade correta:
CREATE UNIQUE INDEX IF NOT EXISTS uq_evento_dfe
  ON bronze.evento_dfe (chave_acesso, tipo_evento, protocolo);

-- Tabela com SK determinística e CNPJ/CPF como chave de negócio
CREATE TABLE IF NOT EXISTS bronze.empresas_clientes (
    sk_empresa        BIGINT PRIMARY KEY,            -- SK determinística (hash do CNPJ/CPF)
    cnpj_cpf          VARCHAR(14) NOT NULL UNIQUE,   -- Natural key
    api_id            TEXT,                          -- Id vindo da API (ex.: "43504-42870875000194")
    nome              TEXT NOT NULL,
    uf_certificado    SMALLINT,
    data_expira       TIMESTAMPTZ,
    consulta_noturna  BOOLEAN,
    ativo             BOOLEAN,
    deletado          BOOLEAN,
    criado_em         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices úteis
CREATE INDEX IF NOT EXISTS ix_empresas_clientes_ativo
  ON bronze.empresas_clientes (ativo)
  WHERE ativo IS TRUE;

-- Trigger para manter atualizado_em
CREATE OR REPLACE FUNCTION bronze.set_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
  NEW.atualizado_em := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_empresas_clientes_set_atualizado_em
ON bronze.empresas_clientes;

CREATE TRIGGER trg_empresas_clientes_set_atualizado_em
BEFORE UPDATE ON bronze.empresas_clientes
FOR EACH ROW
EXECUTE FUNCTION bronze.set_atualizado_em();

-- Comentários
COMMENT ON TABLE bronze.empresas_clientes IS 'Empresas clientes da API SIEG; SK determinística baseada no CNPJ/CPF.';
COMMENT ON COLUMN bronze.empresas_clientes.sk_empresa IS 'Surrogate key (BIGINT) gerada de forma determinística a partir do CNPJ/CPF.';
COMMENT ON COLUMN bronze.empresas_clientes.cnpj_cpf IS 'Chave de negócio (somente dígitos).';
COMMENT ON COLUMN bronze.empresas_clientes.api_id IS 'Identificador retornado pela API SIEG.';
COMMENT ON COLUMN bronze.empresas_clientes.nome IS 'Nome da empresa cliente.';
COMMENT ON COLUMN bronze.empresas_clientes.uf_certificado IS 'UF do certificado, ex.: 51 = MT';
COMMENT ON COLUMN bronze.empresas_clientes.data_expira IS 'Data/hora de expiração do certificado em UTC';
COMMENT ON COLUMN bronze.empresas_clientes.consulta_noturna IS 'Indica se a empresa pode ser consultada à noite';
COMMENT ON COLUMN bronze.empresas_clientes.ativo IS 'Indica se a empresa está ativa';
COMMENT ON COLUMN bronze.empresas_clientes.deletado IS 'Indica se a empresa foi deletada (soft delete)';
COMMENT ON COLUMN bronze.empresas_clientes.criado_em IS 'Data/hora de criação do registro';
COMMENT ON COLUMN bronze.empresas_clientes.atualizado_em IS 'Data/hora da última atualização do registro';

ALTER TABLE bronze.identificacao_dfe
  ADD CONSTRAINT uq_identificacao_dfe_chave UNIQUE (chave_acesso);

CREATE UNIQUE INDEX IF NOT EXISTS uq_evento_dfe
  ON bronze.evento_dfe (chave_acesso, tipo_evento, protocolo);
