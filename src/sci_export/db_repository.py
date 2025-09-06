from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import List
import psycopg2
from settings import Settings
from utils import only_digits


class Paper(str):
    EMITENTE = "emitente"
    DESTINATARIO = "destinatario"
    AMBOS = "ambos"


@dataclass
class DBRow:
    s3_uri: str
    data_emissao: date
    chave_acesso: str
    cnpj_emit: str
    cnpj_dest: str
    tipo_documento: str


class DBRepository:
    """Leitura da tabela `bronze.identificacao_dfe` para listar XMLs no S3."""
    def __init__(self, st: Settings) -> None:
        self._st = st
        self._conn = psycopg2.connect(
            host=st.db_host,
            port=st.db_port,
            database=st.db_name,
            user=st.db_user,
            password=st.db_pass,
            connect_timeout=10,
        )
        self._conn.autocommit = True


    def close(self) -> None:
        try:
            self._conn.close()
        except Exception: # pragma: no cover
            pass


    def list_s3_uris(self, cnpj: str, inicio: date, fim: date, papel: str) -> List[DBRow]:
        c = only_digits(cnpj)
        where_role = {
            Paper.EMITENTE: "regexp_replace(cnpjcpf_emitente, '\\D', '', 'g') = %(cnpj)s",
            Paper.DESTINATARIO: "regexp_replace(cnpjcpf_destinatario, '\\D', '', 'g') = %(cnpj)s",
            Paper.AMBOS: "(regexp_replace(cnpjcpf_emitente, '\\D', '', 'g') = %(cnpj)s OR regexp_replace(cnpjcpf_destinatario, '\\D', '', 'g') = %(cnpj)s)",
        }[papel]
        sql = f"""
            SELECT endereco_s3, data_emissao::date, chave_acesso,
            coalesce(cnpjcpf_emitente,''), coalesce(cnpjcpf_destinatario,''), coalesce(tipo_documento,'')
            FROM bronze.identificacao_dfe
            WHERE {where_role}
            AND data_emissao::date BETWEEN %(ini)s AND %(fim)s
            AND (tipo_documento ILIKE 'NF%%' OR tipo_documento IS NULL OR tipo_documento = '')
            AND endereco_s3 ILIKE 's3://%%.xml'
        """
        out: List[DBRow] = []
        with self._conn.cursor() as cur:
            cur.execute(sql, {"ini": inicio, "fim": fim, "cnpj": c})
            rows = cur.fetchall()  # <- pega os dados antes de fechar o cursor

        for (uri, dt, chave, cem, cde, tipo) in rows:
            out.append(DBRow(
                s3_uri=uri,
                data_emissao=dt,
                chave_acesso=only_digits(chave),
                cnpj_emit=only_digits(cem),
                cnpj_dest=only_digits(cde),
                tipo_documento=(tipo or "").lower(),
            ))
        return out