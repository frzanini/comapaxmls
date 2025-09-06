from __future__ import annotations
from typing import Tuple
import boto3
from botocore.config import Config

class S3Client:
    """Cliente mínimo para recuperar conteúdo de XML (texto) a partir de URI S3."""
    def __init__(self, region_name: str) -> None:
        self._cli = boto3.client(
            "s3",
            region_name=region_name,
            config=Config(
                retries={"max_attempts": 10, "mode": "standard"},
                connect_timeout=10,
                read_timeout=60,
                tcp_keepalive=True,
            ),
        )

    @staticmethod
    def _parse_uri(uri: str) -> Tuple[str, str]:
        assert uri.startswith("s3://"), f"URI inválida: {uri}"
        token = uri.replace("s3://", "", 1)
        bucket, key = token.split("/", 1)
        return bucket, key

    def get_text(self, s3_uri: str) -> str:
        b, k = self._parse_uri(s3_uri)
        obj = self._cli.get_object(Bucket=b, Key=k)
        return obj["Body"].read().decode("utf-8", errors="ignore")
