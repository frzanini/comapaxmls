# =============================
# File: sci/__init__.py
# =============================
"""Pacote SCI: geração de arquivos TXT (Anexo 04, 07, 09) a partir de DF-e.
Componentes:
- settings: leitura de variáveis/paths
- db_repository: consulta URIs S3 no banco
- s3_client: download de XMLs do S3
- dfenew_adapter: parser DFeNew (com fallback)
- domain: modelos de domínio
- layouts: definição dos layouts SCI
- formatter: regras A/N/I/L
- mappers: NFe -> linhas dos anexos
- exporter: orquestra geração
- cli: interface de linha de comando
"""


__all__ = [
"settings", "db_repository", "s3_client", "dfenew_adapter",
"domain", "layouts", "formatter", "mappers", "exporter",
]