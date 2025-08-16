import os
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import logging


def get_s3_client() -> boto3.client:
    """
    Cria cliente boto3 com base nas variáveis de ambiente.
    """
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("S3_REGION", "us-east-1")

    if not aws_access_key or not aws_secret_key:
        raise EnvironmentError("❌ Variáveis AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY não definidas.")

    return boto3.client(
        "s3",
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
    )


def construir_s3_key(cnpj_emit: str, data_emissao: str, nome_arquivo: str) -> str:
    """
    Gera a key (prefixo + nome) do objeto no S3.

    Args:
        cnpj_emit: CNPJ do emitente (somente números)
        data_emissao: Data no formato YYYY-MM-DD
        nome_arquivo: Nome do arquivo a ser enviado

    Returns:
        Caminho do objeto no S3
    """
    ano, mes, _ = data_emissao.split("-")
    return f"documentos/{cnpj_emit}/{ano}/{mes}/{nome_arquivo}"


def upload_file_to_s3(
    bucket_name: str,
    file_path: str,
    cnpj_emit: str,
    data_emissao: str,
    s3_key_prefix: Optional[str] = None,
) -> None:
    """
    Realiza o upload de um arquivo XML para o S3 organizado por CNPJ/ano/mês.

    Args:
        bucket_name: Nome do bucket S3
        file_path: Caminho local do arquivo XML
        cnpj_emit: CNPJ do emitente
        data_emissao: Data de emissão no formato YYYY-MM-DD
        s3_key_prefix: Prefixo customizado (opcional)
    """
    s3 = get_s3_client()
    file_name = Path(file_path).name

    s3_key = (
        f"{s3_key_prefix}/{file_name}" if s3_key_prefix
        else construir_s3_key(cnpj_emit, data_emissao, file_name)
    )

    try:
        s3.upload_file(file_path, bucket_name, s3_key)
        print(f"✅ Upload concluído: s3://{bucket_name}/{s3_key}")
    except (BotoCoreError, ClientError) as e:
        print(f"❌ Falha no upload: {e}")


def upload_string_to_s3(
        bucket_name: str,
        content: str,
        cnpj_emit: str,
        data_emissao: str,
        file_name: str
    ) -> bool:
    """
    Faz upload de conteúdo string (ex: XML) diretamente ao S3, usando chave construída.
    Retorna True se o upload for bem-sucedido, False caso contrário.
    """
    s3 = get_s3_client()
    s3_key = construir_s3_key(cnpj_emit, data_emissao, file_name)

    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=content.encode("utf-8")
        )
        logging.info(f"✅ Upload concluído: s3://{bucket_name}/{s3_key}")
        return True
    except (BotoCoreError, ClientError) as e:
        logging.error(f"❌ Falha no upload para s3://{bucket_name}/{s3_key} - {type(e).__name__}: {e}")
        return False

# upload_dfe_s3.py
def upload_string_to_s3_with_client(
    s3_client,
    bucket_name: str,
    content: str,
    cnpj_emit: str,
    data_emissao: str,
    file_name: str
) -> bool:
    
    s3_key = construir_s3_key(cnpj_emit, data_emissao, file_name)
    
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=content.encode("utf-8"),
            ContentType="application/xml; charset=utf-8",
        )
        logging.info(f"Upload OK: s3://{bucket_name}/{s3_key}")
        return True
    except Exception as e:
        logging.error(f"Falha upload: s3://{bucket_name}/{s3_key} | {e}")
        return False

# ==== Exemplo de uso ====
if __name__ == "__main__":
    # Defina estas variáveis conforme seu caso
    bucket = "comapaxml"
    arquivo = r"C:\workspacePython\comapaxmls\src\temp\2024\10\01\NFE\03954227000245\32241003954227000245550010000036981331333858_NF-e.xml"
    cnpj = "03954227000245"
    data_emissao = "2024-10-01"

    upload_file_to_s3(
        bucket_name=bucket,
        file_path=arquivo,
        cnpj_emit=cnpj,
        data_emissao=data_emissao,
    )
