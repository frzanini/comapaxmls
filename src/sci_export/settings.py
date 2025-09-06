# =============================
# File: sci/settings.py
# =============================
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    """Configuração do pacote SCI via variáveis de ambiente."""
    db_host: str = os.getenv("DB_HOST", "")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "")
    db_user: str = os.getenv("DB_USER", "")
    db_pass: str = os.getenv("DB_PASSWORD", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "./out_sci"))


    def validate(self) -> None:
        missing = [k for k, v in {
        "DB_HOST": self.db_host,
        "DB_NAME": self.db_name,
        "DB_USER": self.db_user,
        "DB_PASSWORD": self.db_pass,
        }.items() if not v]
        if missing:
            raise ValueError(f"Variáveis de ambiente faltando: {', '.join(missing)}")