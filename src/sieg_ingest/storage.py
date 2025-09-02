# s3_storage.py
from __future__ import annotations

import base64
import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

import boto3
from botocore.config import Config as BotoCfg
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class S3Config:
    """
    Configuração do S3Storage.

    Env suportadas (fallbacks):
      - S3_BUCKET (obrigatório em from_env)
      - S3_REGION (default: us-east-1)
      - S3_PREFIX (default: documentos)
      - S3_SSE = "" | "AES256" | "aws:kms" (default: AES256)
      - S3_KMS_KEY_ID (opcional quando S3_SSE==aws:kms)
      - S3_MAX_RETRIES (default: 5)
      - S3_MAX_POOL (default: 64)
    """
    bucket: str
    region: str = os.getenv("S3_REGION", "us-east-1")
    prefix: str = os.getenv("S3_PREFIX", "documentos")
    sse: Literal["", "AES256", "aws:kms"] = os.getenv("S3_SSE", "AES256")
    kms_key_id: Optional[str] = os.getenv("S3_KMS_KEY_ID") or None
    max_retries: int = int(os.getenv("S3_MAX_RETRIES", "5"))
    max_pool: int = int(os.getenv("S3_MAX_POOL", "64"))
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")

    @staticmethod
    def from_env() -> "S3Config":
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise EnvironmentError("S3_BUCKET não definido no ambiente.")
        return S3Config(bucket=bucket)


class S3Storage:
    """
    Storage otimizado para XML em S3.

    - Idempotência opcional via if_exists="skip" (faz HEAD antes do PUT).
    - Criptografia do lado do servidor: AES256 ou KMS.
    - Content-MD5 correto (base64 do digest binário) para validação de integridade.
    - Pool e retries via botocore.Config para throughput em Lambda.

    API:
        put_xml_string(content, cnpj_emit, data_emissao, file_name, if_exists="skip")

    Exemplo:
        storage = S3Storage.from_env()
        storage.put_xml_string(
            content=xml_str,
            cnpj_emit="12345678000199",
            data_emissao="2025-08-16T10:25:00-03:00",
            file_name="35140812345678000199550010000000011000000010_NFE.xml",
            if_exists="overwrite",
        )
    """

    def __init__(self, cfg: S3Config, client=None) -> None:
        self.cfg = cfg
        self.client = client or boto3.client(
            "s3",
            region_name=cfg.s3_region,
            aws_access_key_id=cfg.s3.access_key_id, #os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=cfg.s3.secret_access_key,  #os.getenv("AWS_SECRET_ACCESS_KEY"),
            config=BotoCfg(
                max_pool_connections=cfg.s3.max_pool,
                retries={"max_attempts": cfg.s3.max_retries, "mode": "standard"},
            ),
        )
        # Normaliza prefix para evitar '//' nas chaves
        self._prefix = (self.cfg.s3.prefix or "").strip().strip("/")
        # Permite prefix vazio (sem 'documentos')
        if self._prefix:
            self._prefix = self._prefix  # já normalizado

    @classmethod
    def from_env(cls) -> "S3Storage":
        return cls(S3Config.from_env())

    # ------------------------- Helpers -------------------------

    @staticmethod
    def _ym_from_date_string(date_str: str) -> tuple[str, str]:
        """
        Aceita "YYYY-MM-DD", "YYYY-MM-DDTHH:MM:SS(.fff)[Z|±HH:MM]" ou "YYYYMMDD".
        Retorna (ano, mes) como strings zero-padded.
        """
        if not date_str:
            # cai no now UTC para não quebrar
            now = datetime.utcnow()
            return f"{now.year:04d}", f"{now.month:02d}"

        s = date_str[:10]  # trunca ISO (YYYY-MM-DD)
        try:
            if len(s) == 10 and s[4] == "-" and s[7] == "-":
                dt = datetime.strptime(s, "%Y-%m-%d")
            elif len(date_str) == 8 and date_str.isdigit():
                dt = datetime.strptime(date_str, "%Y%m%d")
            else:
                # fallback: tenta fromisoformat
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            now = datetime.utcnow()
            return f"{now.year:04d}", f"{now.month:02d}"
        return f"{dt.year:04d}", f"{dt.month:02d}"

    def _build_key(self, cnpj_emit: str, data_emissao: str, file_name: str) -> str:
        ano, mes = self._ym_from_date_string(data_emissao)
        cnpj = "".join(ch for ch in (cnpj_emit or "") if ch.isdigit())
        parts = [p for p in [self._prefix, cnpj, ano, mes, file_name] if p]
        return "/".join(parts)

    def _exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.cfg.s3_bucket, Key=key)
            return True
        except ClientError as e:
            # 404 = Not Found; 403 pode ser permissão — não vamos tratar como existente
            status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 404:
                return False
            # Relevante deixar emergir outros erros
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
        Sobe um XML em S3:
         - Caminho: <prefix>/<cnpj>/<ano>/<mes>/<file_name>
         - Validação Content-MD5 (integridade).
         - SSE AES256/KMS conforme config.

        :param content: XML como string (UTF-8).
        :param cnpj_emit: CNPJ do emitente (com ou sem máscara).
        :param data_emissao: Data ISO ou "YYYY-MM-DD" (aceita variantes).
        :param file_name: Nome final do arquivo .xml (determinístico de preferência).
        :param if_exists: "skip" (idempotente com HEAD) ou "overwrite" (mais performático).
        :param extra_metadata: dicionário opcional para gravação em Metadata do S3.
        """
        key = self._build_key(cnpj_emit, data_emissao, file_name)

        if if_exists == "skip":
            try:
                if self._exists(key):
                    logger.info("Já existe, pulando: s3://%s/%s", self.cfg.s3_bucket, key)
                    return True
            except ClientError as e:
                # Se 403, ainda tentamos PUT (permissões podem diferir entre HEAD/PUT).
                status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if status not in (403, 404):
                    raise

        put_kwargs = {
            "Bucket": self.cfg.s3_bucket,
            "Key": key,
            "Body": content.encode("utf-8"),
            "ContentType": "application/xml; charset=utf-8",
            "ContentMD5": self._content_md5_b64(content),  # remove se não quiser validação MD5 no S3
        }

        # Criptografia
        if self.cfg.sse == "AES256":
            put_kwargs["ServerSideEncryption"] = "AES256"
        elif self.cfg.sse == "aws:kms":
            put_kwargs["ServerSideEncryption"] = "aws:kms"
            if self.cfg.kms_key_id:
                put_kwargs["SSEKMSKeyId"] = self.cfg.kms_key_id

        # Metadata custom (chaves precisam ser strings)
        if extra_metadata:
            put_kwargs["Metadata"] = {str(k): str(v) for k, v in extra_metadata.items()}

        try:
            self.client.put_object(**put_kwargs)
            logger.info("Upload OK: s3://%s/%s", self.cfg.bucket, key)
            return True
        except (BotoCoreError, ClientError) as e:
            logger.error("Falha no upload s3://%s/%s: %s", self.cfg.bucket, key, e)
            return False

    # --- Backward-compat com o serviço que chama 'upload_parsed' ---
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
        """
        Mantém compatibilidade com o serviço existente:
        SiegIngestionService -> S3Storage.upload_parsed(...)
        """
        return self.put_xml_string(
            content=xml_text,
            cnpj_emit=cnpj_emit,
            data_emissao=data_ymd,   # aceita ISO; método interno trunca
            file_name=file_name,
            if_exists=if_exists,
            extra_metadata=extra_metadata,
        )
