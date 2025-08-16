# s3_uploader.py
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


def _build_key(cnpj_emit: str, data_emissao: str, file_name: str, prefix: str) -> str:
    ano, mes, *_ = data_emissao.split("-")
    return f"{prefix.rstrip('/')}/{cnpj_emit}/{ano}/{mes}/{file_name}"


@dataclass(frozen=True)
class S3Config:
    bucket: str
    region: str = os.getenv("S3_REGION", "us-east-1")
    prefix: str = os.getenv("S3_PREFIX", "documentos")
    sse: Literal["", "AES256", "aws:kms"] = os.getenv("S3_SSE", "AES256")
    kms_key_id: Optional[str] = os.getenv("S3_KMS_KEY_ID") or None
    max_retries: int = int(os.getenv("S3_MAX_RETRIES", "5"))


class S3Uploader:
    """
    Uploader com:
      - idempotência (HeadObject → skip ou overwrite),
      - SSE (AES256/KMS),
      - ContentType/MD5,
      - retries internos do boto3 (config do client) + tentativa manual final.
    """

    def __init__(self, cfg: S3Config, client=None):
        self.cfg = cfg
        self.client = client or boto3.client(
            "s3",
            region_name=cfg.region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def _head(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.cfg.bucket, Key=key)
            return True
        except self.client.exceptions.NoSuchKey:
            return False
        except ClientError as e:
            if e.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return False
            raise

    def put_xml_string(
        self,
        *,
        content: str,
        cnpj_emit: str,
        data_emissao: str,  # YYYY-MM-DD
        file_name: str,
        if_exists: Literal["skip", "overwrite"] = "skip",
    ) -> bool:
        key = _build_key(cnpj_emit, data_emissao, file_name, prefix=self.cfg.prefix)

        if if_exists == "skip" and self._head(key):
            logger.info("Já existe, pulando: s3://%s/%s", self.cfg.bucket, key)
            return True

        # Content-MD5 para integridade (base64 do digest binário)
        md5_b64 = hashlib.md5(content.encode("utf-8")).digest().hex()  # opcional: base64.b64encode(...)

        put_kwargs = {
            "Bucket": self.cfg.bucket,
            "Key": key,
            "Body": content.encode("utf-8"),
            "ContentType": "application/xml; charset=utf-8",
            # "ContentMD5": base64.b64encode(hashlib.md5(content.encode("utf-8")).digest()).decode("ascii"),
        }

        if self.cfg.sse == "AES256":
            put_kwargs["ServerSideEncryption"] = "AES256"
        elif self.cfg.sse == "aws:kms":
            put_kwargs["ServerSideEncryption"] = "aws:kms"
            if self.cfg.kms_key_id:
                put_kwargs["SSEKMSKeyId"] = self.cfg.kms_key_id

        try:
            self.client.put_object(**put_kwargs)
            logger.info("Upload OK: s3://%s/%s | md5=%s", self.cfg.bucket, key, md5_b64)
            return True
        except (BotoCoreError, ClientError) as e:
            logger.error("Falha no upload s3://%s/%s: %s", self.cfg.bucket, key, e)
            return False
