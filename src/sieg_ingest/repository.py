from __future__ import annotations
import os, psycopg2
from typing import Iterable, Tuple

class CompanyRepository:
    @staticmethod
    def connect_from_env():
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST","localhost"),
            port=int(os.getenv("DB_PORT","5432")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DB_NAME"),
        )
        conn.autocommit = True
        return conn

    @staticmethod
    def iter_empresas(conn) -> Iterable[Tuple[int,str]]:
        sql = """
        SELECT sk_empresa, cnpj_cpf
          FROM bronze.empresas_clientes
         WHERE COALESCE(ativo,FALSE)=TRUE
           AND COALESCE(deletado,FALSE)=FALSE
           AND (data_expira IS NULL OR data_expira>=NOW())
           AND cnpj_cpf IS NOT NULL
         ORDER BY sk_empresa
        """
        with conn.cursor() as cur:
            cur.execute(sql)
            yield from cur
