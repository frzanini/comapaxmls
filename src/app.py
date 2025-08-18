# app.py
from datetime import datetime
from sieg_client import SiegClient, XmlType
from s3_uploader import S3Uploader, S3Config
from dfe_downloader import DFeDownloader
import os
from dotenv import load_dotenv
import logging

if __name__ == "__main__":
    uploader = S3Uploader(S3Config(bucket=os.getenv("S3_BUCKET", "comapaxml")))
    client = DFeDownloader.from_env(uploader=uploader)

    data_inicio = datetime(2025, 4, 1)
    data_fim = datetime(2025, 4, 30)

    client.download_skip(
        start_date=data_inicio,
        end_date=data_fim,
        xml_types=[XmlType.NFE],        ##XmlType.CTE, XmlType.NFCE, XmlType.CFE),  # NFSe use client.download_nfse
        include_events=False,
        cnpj_cpf_emit="24670826000126"  # Exemplo de CNPJ
    )
