# lambda_function.py
import os
import logging
from typing import Any, Dict, Tuple

# Importa sua classe (ajuste o caminho se necessário)
from DFEIngestor import DFEIngestor

logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))

# Opcional: instanciar fora do handler para reaproveitar conexões entre invocações (melhor cold-start)
# Se você usa variáveis dinâmicas diferentes a cada invocação, prefira instanciar no handler.
_INGESTOR_SINGLETON = None if os.getenv("DFE_INGESTOR_SINGLETON", "true").lower() != "true" else DFEIngestor()


def _run_full_import(ingestor: DFEIngestor) -> Tuple[int, int]:
    """
    Executa a importação completa (clientes + não clientes).
    Retorna (docs, eventos) inseridos.
    """
    # A versão atual do executar() já faz logs e fecha a conexão ao final.
    # Para capturar totais, você pode eventualmente retornar os contadores de executar().
    # Aqui, só chamamos e retornamos 0,0 como "placeholder" de resposta (os logs trarão os números).
    ingestor.executar()
    return (0, 0)


def _run_targeted_import(ingestor: DFEIngestor, cnpj: str, ano: int, mes: int) -> Tuple[int, int]:
    """
    Executa a importação pontual por CNPJ+ano+mês.
    Retorna (docs, eventos) inseridos no batch.
    """
    docs, eventos = ingestor.ingerir_emitente_ano_mes(cnpj, ano, mes)
    return (docs, eventos)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler.

    Comportamento:
      - Se as variáveis de ambiente TARGET_CNPJ, TARGET_ANO, TARGET_MES estiverem presentes,
        roda a ingestão pontual daquele prefixo.
      - Caso contrário, roda a importação completa.

    Variáveis de ambiente necessárias (exemplos):
      # S3 / Parser
      S3_BUCKET=<nome-do-bucket>
      DEFAULT_PREFIX=documentos/  # opcional (default "documentos/")

      # Banco de dados
      DB_HOST=<host>
      DB_PORT=5432
      DB_NAME=<dbname>
      DB_USER=<user>
      DB_PASSWORD=<password>

      # Ajustes de desempenho (opcionais)
      BULK_BATCH_SIZE=2000
      MAX_WORKERS=8
      INCLUDE_NON_CLIENT_EMITTERS=true
      S3_ONLY_LAST_HOURS=24
      PG_STMT_TIMEOUT_MS=60000
      AWS_RETRY_ATTEMPTS=10

      # Modo pontual (opcionais)
      TARGET_CNPJ=32989568000173
      TARGET_ANO=2025
      TARGET_MES=6

      # Reaproveitar instância da classe entre invocações
      DFE_INGESTOR_SINGLETON=true
    """
    # Decide se é pontual ou completo pelos ENV (ignora .env)
    target_cnpj = os.getenv("TARGET_CNPJ")
    target_ano = os.getenv("TARGET_ANO")
    target_mes = os.getenv("TARGET_MES")

    # Instancia a classe (reuso opcional do singleton)
    ingestor = _INGESTOR_SINGLETON or DFEIngestor()

    try:
        if target_cnpj and target_ano and target_mes:
            ano = int(target_ano)
            mes = int(target_mes)
            logger.info(
                "Iniciando ingestão pontual via ENV: CNPJ=%s, Ano=%d, Mes=%d",
                target_cnpj, ano, mes
            )
            docs, eventos = _run_targeted_import(ingestor, target_cnpj, ano, mes)

            result = {
                "mode": "targeted",
                "cnpj": target_cnpj,
                "ano": ano,
                "mes": mes,
                "docs_inserted": docs,
                "eventos_inserted": eventos,
                "status": "OK"
            }
            logger.info("Concluído (pontual): %s", result)
            return result

        # Fallback: FULL
        logger.info("Iniciando importação FULL (clientes + não clientes).")
        docs, eventos = _run_full_import(ingestor)

        result = {
            "mode": "full",
            "docs_inserted": docs,      # ver nota no _run_full_import
            "eventos_inserted": eventos,
            "status": "OK"
        }
        logger.info("Concluído (full): %s", result)
        return result

    except Exception as e:
        logger.exception("Falha na execução da ingestão: %s", e)
        return {
            "status": "ERROR",
            "error": str(e)
        }
