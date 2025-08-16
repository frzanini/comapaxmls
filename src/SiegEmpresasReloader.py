"""
Carrega empresas clientes da SIEG em PostgreSQL usando TRUNCATE + RELOAD,
com SK determinística (BIGINT) derivada do CNPJ/CPF.

Requisitos:
  pip install requests psycopg2-binary python-dotenv

Variáveis de ambiente:
  SIEG_API_KEY
  DB_HOST
  DB_PORT=5432
  DB_NAME=postgres
  DB_USER
  DB_PASSWORD
  DB_SCHEMA=bronze            (opcional)
  DB_TABLE=empresas_clientes  (opcional)
"""

from __future__ import annotations

import os
import logging
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import requests
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

API_URL = "https://api.sieg.com/api/Certificado/ListarCertificados"


def _env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None:
        raise RuntimeError(f"Variável de ambiente obrigatória ausente: {name}")
    return v


def _only_digits(s: str) -> str:
    return "".join(ch for ch in s or "" if ch.isdigit())


def sk_from_cnpj_cpf(cnpj_cpf: str) -> int:
    """
    SK determinística BIGINT > 0 a partir do CNPJ/CPF (somente dígitos).
    Estratégia: MD5(cnpj_cpf) -> primeiros 8 bytes -> inteiro sem sinal -> força positivo.
    """
    base = _only_digits(cnpj_cpf)
    h = hashlib.md5(base.encode("utf-8")).digest()  # 16 bytes
    # pega os primeiros 8 bytes como inteiro sem sinal (big endian)
    val = int.from_bytes(h[:8], byteorder="big", signed=False)
    # força positivo dentro do range signed BIGINT (0..2^63-1)
    return val & 0x7FFF_FFFF_FFFF_FFFF


class SiegEmpresasReloader:
    """TRUNCATE + RELOAD com SK determinística por CNPJ/CPF."""

    def __init__(self) -> None:
        self.api_key = _env("API_KEY")
        self.db = {
            "host": _env("DB_HOST"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "dbname": _env("DB_NAME", "postgres"),
            "user": _env("DB_USER"),
            "password": _env("DB_PASSWORD"),
        }
        self.schema = os.getenv("DB_SCHEMA", "bronze")
        self.table = os.getenv("DB_TABLE", "empresas_clientes")

    # ---------- API ----------
    def fetch_empresas(self) -> List[Dict[str, Any]]:
        url = f"{API_URL}?active=true&api_key={self.api_key}"
        logging.info("Consultando SIEG...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise ValueError("Resposta inesperada: não é uma lista.")
        logging.info("Recebidas %d empresas.", len(data))
        return data

    # ---------- DB ----------
    def ensure_table(self, cur) -> None:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.{self.table} (
                sk_empresa        BIGINT PRIMARY KEY,
                cnpj_cpf          VARCHAR(14) NOT NULL UNIQUE,
                api_id            TEXT,
                nome              TEXT NOT NULL,
                uf_certificado    SMALLINT,
                data_expira       TIMESTAMPTZ,
                consulta_noturna  BOOLEAN,
                ativo             BOOLEAN,
                deletado          BOOLEAN,
                criado_em         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                atualizado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS ix_{self.table}_ativo
            ON {self.schema}.{self.table} (ativo)
            WHERE ativo IS TRUE;
            """
        )
        cur.execute(
            f"""
            CREATE OR REPLACE FUNCTION {self.schema}.set_atualizado_em()
            RETURNS TRIGGER AS $$
            BEGIN
              NEW.atualizado_em := NOW();
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        cur.execute(
            f"""
            DROP TRIGGER IF EXISTS trg_{self.table}_set_atualizado_em
            ON {self.schema}.{self.table};
            """
        )
        cur.execute(
            f"""
            CREATE TRIGGER trg_{self.table}_set_atualizado_em
            BEFORE UPDATE ON {self.schema}.{self.table}
            FOR EACH ROW
            EXECUTE FUNCTION {self.schema}.set_atualizado_em();
            """
        )

    @staticmethod
    def _parse_dt(dt: Optional[str]) -> Optional[datetime]:
        if not dt:
            return None
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))

    def _to_row(self, e: Dict[str, Any]) -> Tuple[Any, ...]:
        cnpj_cpf = _only_digits(e.get("CnpjCpf", ""))
        if not cnpj_cpf:
            raise ValueError("Registro da API sem CnpjCpf válido.")
        sk = sk_from_cnpj_cpf(cnpj_cpf)
        return (
            sk,                              # sk_empresa
            cnpj_cpf,                        # cnpj_cpf (natural key)
            e.get("Id"),                     # api_id
            e.get("Nome"),                   # nome
            e.get("UfCertificado"),          # uf_certificado
            self._parse_dt(e.get("DataExpira")),  # data_expira
            e.get("ConsultaNoturna"),        # consulta_noturna
            e.get("Ativo"),                  # ativo
            e.get("Deletado"),               # deletado
        )

    def reload(self, empresas: List[Dict[str, Any]]) -> None:
        if not empresas:
            logging.warning("Lista vazia recebida. Abortando para evitar apagar dados.")
            return

        conn = psycopg2.connect(**self.db)
        try:
            with conn:
                with conn.cursor() as cur:
                    self.ensure_table(cur)

                    logging.info("TRUNCATE %s.%s ...", self.schema, self.table)
                    cur.execute(f"TRUNCATE TABLE {self.schema}.{self.table};")

                    logging.info("Inserindo %d registros (bulk)...", len(empresas))
                    rows = [self._to_row(e) for e in empresas]
                    execute_values(
                        cur,
                        f"""
                        INSERT INTO {self.schema}.{self.table} (
                            sk_empresa, cnpj_cpf, api_id, nome, uf_certificado,
                            data_expira, consulta_noturna, ativo, deletado
                        ) VALUES %s
                        """,
                        rows,
                        page_size=2000,
                    )

                    cur.execute(f"ANALYZE {self.schema}.{self.table};")
            logging.info("Reload concluído com sucesso.")
        finally:
            conn.close()

    def run(self) -> None:
        empresas = self.fetch_empresas()
        self.reload(empresas)


if __name__ == "__main__":
    SiegEmpresasReloader().run()
