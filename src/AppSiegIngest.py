# app.py
import logging
from sieg_ingest.config import SiegConfig
from sieg_ingest.service import SiegIngestionService
from sieg_ingest.types import XmlType
from datetime import datetime, timezone, timedelta
from typing import List


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def main() -> None:
    # carrega as configs do .env (já previsto no SiegConfig)
    cfg = SiegConfig.from_env()

    print(cfg)

    # instancia o serviço principal
    service = SiegIngestionService(cfg)

    # executa ingestão simples de teste (ajuste os params se quiser filtrar)
    logging.info("Iniciando ingestão de teste...")
    
    # service.baixar_intervalo_dias(
    #     days_back=5,
    #     xml_types=[XmlType.NFE],
    #     include_events=False,
    #     cnpj="24670826000126",
    #     participante="emitente"
    # )  # Exemplo: filtrar por CNPJ/CPF destinatário
    # 34.228.897/0001-27 | 34228897000127 | FERRAGENS LDA
    # 24.670.826/0001-26 | 24670826000126 | COMAPAR COMERCIO DE MAQUINAS E PECAS LTDA
    # 08.959.064/0001-26 | 08959064000126 | J B RECICLAGEM LTDA
    service.baixar_por_cnpj_ano_mes(
        cnpj="08959064000126",
        year=2025,
        month=8,
        incluir_eventos=False,
        xml_types=[XmlType.NFE, XmlType.CTE, XmlType.NFCE, XmlType.CFE, XmlType.MDFE],
        participante="ambos",
        incluir_dest_quando_emitente=True
    )  # Exemplo: baixar por CNPJ/ano/mês
        
    logging.info("Ingestão concluída.")

if __name__ == "__main__":
    main()
