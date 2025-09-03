# storage.py
from __future__ import annotations

import base64
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Any

import boto3
from botocore.config import Config as BotoCfg
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


# Opcional: helper de config direta por ENV (quando não vier um S3Section)
@dataclass(frozen=True)
class S3Config:
    bucket: str
    region: str = "us-east-1"
    prefix: str = "documentos"
    sse: Literal["", "AES256", "aws:kms"] = "AES256"
    kms_key_id: Optional[str] = None
    max_retries: int = 5
    max_pool: int = 64

    @staticmethod
    def from_env() -> "S3Config":
        import os
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise EnvironmentError("S3_BUCKET não definido no ambiente.")
        return S3Config(
            bucket=bucket,
            region=os.getenv("S3_REGION", "us-east-1"),
            prefix=os.getenv("S3_PREFIX", "documentos"),
            sse=os.getenv("S3_SSE", "AES256"),
            kms_key_id=os.getenv("S3_KMS_KEY_ID") or None,
            max_retries=int(os.getenv("S3_MAX_RETRIES", "5")),
            max_pool=int(os.getenv("S3_MAX_POOL", "64")),
        )


class S3Storage:
    """
    Storage S3 para XML com:
      - Caminho: <prefix>/<cnpj>/<ano>/<mes>/<file_name>
      - HEAD opcional (if_exists="skip") para idempotência
      - SSE AES256/KMS
      - Content-MD5 para integridade
    """

    def __init__(self, cfg: Any, s3_client=None) -> None:
        # Aceita SiegConfig (usa .s3) ou S3Section/S3Config diretamente
        self.cfg = getattr(cfg, "s3", cfg)

        # Constrói cliente S3 (ou usa injetado para testes)
        self.s3 = s3_client or boto3.client(
            "s3",
            region_name=self.cfg.region,
            config=BotoCfg(
                retries={"max_attempts": getattr(self.cfg, "max_retries", 5), "mode": "standard"},
                max_pool_connections=getattr(self.cfg, "max_pool", 64),
            ),
        )
        # Alias para compatibilidade com código legado
        self.client = self.s3

    # ------------------------- Helpers -------------------------

    @staticmethod
    def _ym_from_date_string(date_str: str) -> tuple[str, str]:
        """
        Aceita: "YYYY-MM-DD", ISO "YYYY-MM-DDTHH:MM:SS(.fff)[Z|±HH:MM]" ou "YYYYMMDD".
        Retorna (ano, mes).
        """
        if not date_str:
            now = datetime.utcnow()
            return f"{now.year:04d}", f"{now.month:02d}"

        s10 = date_str[:10]
        try:
            if len(s10) == 10 and s10[4] == "-" and s10[7] == "-":
                dt = datetime.strptime(s10, "%Y-%m-%d")
            elif len(date_str) == 8 and date_str.isdigit():
                dt = datetime.strptime(date_str, "%Y%m%d")
            else:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            now = datetime.utcnow()
            return f"{now.year:04d}", f"{now.month:02d}"
        return f"{dt.year:04d}", f"{dt.month:02d}"

    @staticmethod
    def _only_digits(text: Optional[str]) -> str:
        return "".join(ch for ch in (text or "") if ch.isdigit())

    def _build_key(self, cnpj_emit: str, data_emissao: str, file_name: str) -> str:
        ano, mes = self._ym_from_date_string(data_emissao)
        cnpj = self._only_digits(cnpj_emit)
        parts = [p for p in [self.cfg.prefix, cnpj, ano, mes, file_name] if p]
        return "/".join(parts)

    def _exists(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.cfg.bucket, Key=key)
            return True
        except ClientError as e:
            status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            # 404 não existe; 403 pode ser permissão — tratamos como não-existência para permitir PUT
            if status in (403, 404):
                return False
            raise

    @staticmethod
    def _content_md5_b64(text: str) -> str:
        raw = hashlib.md5(text.encode("utf-8")).digest()
        return base64.b64encode(raw).decode("ascii")

    # ---------------------- API pública -----------------------

    def put_xml_string(
        self,
        *,
        content: str,
        cnpj_emit: str,
        data_emissao: str,
        file_name: str,
        if_exists: Literal["skip", "overwrite"] = "skip",
        extra_metadata: Optional[dict] = None,
    ) -> bool:
        """
        Envia um XML para o S3 com validação MD5 e SSE.
        """
        key = self._build_key(cnpj_emit, data_emissao, file_name)

        if if_exists == "skip":
            try:
                if self._exists(key):
                    logger.info("Já existe, pulando: s3://%s/%s", self.cfg.bucket, key)
                    return True
            except ClientError as e:
                status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if status not in (403, 404):
                    raise

        put_kwargs = {
            "Bucket": self.cfg.bucket,
            "Key": key,
            "Body": content.encode("utf-8"),
            "ContentType": "application/xml; charset=utf-8",
            "ContentMD5": self._content_md5_b64(content),
        }

        # Criptografia
        if getattr(self.cfg, "sse", "") == "AES256":
            put_kwargs["ServerSideEncryption"] = "AES256"
        elif getattr(self.cfg, "sse", "") == "aws:kms":
            put_kwargs["ServerSideEncryption"] = "aws:kms"
            kms = getattr(self.cfg, "kms_key_id", None)
            if kms:
                put_kwargs["SSEKMSKeyId"] = kms

        # Metadata extra (normalizada para str)
        if extra_metadata:
            put_kwargs["Metadata"] = {str(k): str(v) for k, v in extra_metadata.items()}

        try:
            self.s3.put_object(**put_kwargs)
            logger.info("Upload OK: s3://%s/%s", self.cfg.bucket, key)
            return True
        except (BotoCoreError, ClientError) as e:
            logger.error("Falha no upload s3://%s/%s: %s", self.cfg.bucket, key, e)
            return False

    # Compat com chamadas existentes do serviço
    def upload_parsed(
        self,
        xml_text: str,
        cnpj_emit: str,
        data_ymd: str,
        file_name: str,
        *,
        if_exists: Literal["skip", "overwrite"] = "skip",
        extra_metadata: Optional[dict] = None,
    ) -> bool:
        return self.put_xml_string(
            content=xml_text,
            cnpj_emit=cnpj_emit,
            data_emissao=data_ymd,
            file_name=file_name,
            if_exists=if_exists,
            extra_metadata=extra_metadata,
        )
