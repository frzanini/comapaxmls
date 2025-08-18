# config.py
from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


def load_project_env() -> str:
    """
    Procura automaticamente o arquivo .env na raiz do projeto e carrega.
    """
    base_dir = Path(__file__).resolve().parent

    for parent in [base_dir] + list(base_dir.parents):
        env_path = parent / ".env"
        if env_path.exists():
            #load_dotenv(dotenv_path=env_path)
            print(f".env carregado de: {env_path}")
            return env_path

    raise FileNotFoundError(".env não encontrado na raiz do projeto.")

print(load_project_env())

#load_dotenv(dotenv_path=os.path.abspath(_ENV_PATH))

# .env opcional
try:
    from dotenv import load_dotenv  # type: ignore
    _DOTENV = True
except Exception:
    _DOTENV = False

# ===== .env opcional =====
_ENV_PATH = load_project_env() 
#os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(_ENV_PATH))

# ================= Seções de Config =================
@dataclass(frozen=True)
class SiegSection:
    api_key: str
    base_url: str                   # ex.: https://api.sieg.com/api/Xml/BuscarXmls
    take: int = 200                 # paginação por chamada
    timeout_s: float = 60.0         # timeout HTTP
    sleep_between_calls_s: float = 3.0  # rate limit mínimo entre chamadas


@dataclass(frozen=True)
class S3Section:
    bucket: str
    region: str
    prefix: str
    access_key_id: str
    secret_access_key: str
    sse: str = "AES256"             # "" | "AES256" | "aws:kms"
    kms_key_id: Optional[str] = None
    max_retries: int = 5
    max_pool: int = 64


@dataclass(frozen=True)
class DBSection:
    host: Optional[str] = None
    port: int = 5432
    name: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None


@dataclass(frozen=True)
class RuntimeSection:
    log_level: str = "INFO"         # DEBUG/INFO/WARN/ERROR
    file_log_path: Optional[str] = None
    file_log_max_bytes: int = 10_000_000
    file_log_backup_count: int = 5


# ================= AppConfig unificado =================
@dataclass(frozen=True)
class SiegConfig:
    sieg: SiegSection
    s3: S3Section
    db: DBSection
    runtime: RuntimeSection

    # --------- Conveniências / compat retro ---------
    @property
    def api_key(self) -> str: return self.sieg.api_key

    @property
    def base_url(self) -> str: return self.sieg.base_url

    @property
    def take(self) -> int: return self.sieg.take

    @property
    def timeout_s(self) -> float: return self.sieg.timeout_s

    @property
    def sleep_between_calls_s(self) -> float: return self.sieg.sleep_between_calls_s

    @property
    def s3_bucket(self) -> str: return self.s3.bucket

    @property
    def s3_region(self) -> str: return self.s3.region

    # --------- Loader ---------
    @staticmethod
    def from_env(env_path: Optional[str] = None) -> "SiegConfig":
        # Carrega .env se existir
        if _DOTENV:
            if env_path and os.path.exists(env_path):
                load_dotenv(dotenv_path=env_path, override=False)
            else:
                # Carrega .env na raiz do projeto
                if _ENV_PATH and os.path.exists(_ENV_PATH):
                    load_dotenv(dotenv_path=_ENV_PATH, override=False)
                else:
                    # tenta .env no CWD por padrão
                    if os.path.exists(".env"):
                        load_dotenv(dotenv_path=".env", override=False)

        # ---------- SIEG ----------
        api_key = os.getenv("SIEG_API_KEY")
        base_url = os.getenv("SIEG_BASE_URL")  # <- só a base agora
        if not api_key or not base_url:
            raise ValueError("Defina API_KEY e SIEG_BASE_URL no ambiente.")

        sieg = SiegSection(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            take=int(os.getenv("SIEG_TAKE")),
            timeout_s=float(os.getenv("SIEG_HTTP_TIMEOUT_S")),
            sleep_between_calls_s=float(os.getenv("SIEG_SLEEP_BETWEEN_CALLS_S")),
        )

        # ---------- S3 ----------
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise ValueError("Defina S3_BUCKET no ambiente.")
        s3 = S3Section(
            bucket=bucket,
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region=os.getenv("S3_REGION"),
            prefix=os.getenv("S3_PREFIX"),
            sse=os.getenv("S3_SSE", "AES256"),
            kms_key_id=os.getenv("S3_KMS_KEY_ID") or None,
            max_retries=int(os.getenv("S3_MAX_RETRIES", "5")),
            max_pool=int(os.getenv("S3_MAX_POOL", "64")),
        )

        # ---------- DB (opcional) ----------
        db = DBSection(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "5432")),
            name=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

        # ---------- Runtime / Logs ----------
        runtime = RuntimeSection(
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            file_log_path=os.getenv("FILE_LOG_PATH") or None,
            file_log_max_bytes=int(os.getenv("FILE_LOG_MAX_BYTES", "10000000")),
            file_log_backup_count=int(os.getenv("FILE_LOG_BACKUP_COUNT", "5")),
        )

        return SiegConfig(sieg=sieg, s3=s3, db=db, runtime=runtime)

    # Helpers úteis
    def require_db_complete(self) -> None:
        """Levanta erro se as credenciais de DB estiverem incompletas."""
        if not (self.db.host and self.db.name and self.db.user and self.db.password):
            raise EnvironmentError("Variáveis DB_* incompletas. Defina DB_HOST, DB_NAME, DB_USER, DB_PASSWORD.")


# ------------- Compat com importações antigas -------------
# Se algum código antigo fazia: `from config import SiegConfig, S3_BUCKET, S3_REGION`
# mantemos símbolos compatíveis apontando para AppConfig.from_env()

# Mantém nomes esperados anteriormente (deprecated, mas funcionais)
def SiegConfig_from_env() -> SiegSection:
    """Compat: devolve apenas a seção SIEG (mantendo assinatura antiga)."""
    cfg = SiegConfig.from_env()
    return cfg.sieg

# Expor S3_BUCKET / S3_REGION como variáveis (mantendo compat)
# Atenção: estes são avaliados no import; prefira AppConfig.from_env() no código novo.
S3_BUCKET = os.getenv("S3_BUCKET") or ""
S3_REGION = os.getenv("S3_REGION", "us-east-1")
