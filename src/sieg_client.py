# sieg_client.py
from __future__ import annotations

import os
import re
import time
import base64
import logging
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import Iterator, Optional, Sequence, Tuple, List, Dict, Iterable

import requests
from requests import Session, Response
from dotenv import load_dotenv

import boto3
from botocore.config import Config as BotoCfg
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import psycopg2  # psycopg2

from dfe.DocumentoFiscalParser import DocumentoFiscalParser
from upload_dfe_s3 import upload_string_to_s3_with_client as upload_string_to_s3

# ===== .env opcional =====
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=os.path.abspath(_ENV_PATH))

# ===== Logging =====
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    # ---- File logging (Rotating) ----
    try:
        from logging.handlers import RotatingFileHandler
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "sieg_client.log")

        file_handler = RotatingFileHandler(
            log_path, maxBytes=int(os.getenv("FILE_LOG_MAX_BYTES", "10000000")),
            backupCount=int(os.getenv("FILE_LOG_BACKUP_COUNT", "5")),
            encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, os.getenv("FILE_LOG_LEVEL", "INFO").upper(), logging.INFO))
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
        logger.addHandler(file_handler)

        # Optionally silence console logs but keep file logs (set LOG_SILENT=1)
        if os.getenv("LOG_SILENT", "").strip() in {"1", "true", "TRUE", "yes", "on"}:
            for h in logging.getLogger().handlers:
                # Keep only file handler active
                if not isinstance(h, RotatingFileHandler):
                    h.setLevel(logging.CRITICAL)
    except Exception as _e:
        # if file logging fails, continue with console-only
        logger.debug("File logging not configured: %s", _e)


class XmlType(IntEnum):
    NFE = 1
    CTE = 2
    NFSE = 3
    NFCE = 4
    CFE = 5


_ONLY_DIGITS = re.compile(r"\\D+")


def _only_digits(v: Optional[str]) -> Optional[str]:
    return _ONLY_DIGITS.sub("", v) if v else v


@dataclass(frozen=True)
class SiegConfig:
    api_key: str
    base_url: str      # ex.: https://api.sieg.com//BaixarXmls
    take: int = int(os.getenv("SIEG_TAKE", "50"))
    timeout_s: int = int(os.getenv("HTTP_TIMEOUT_S", "30"))
    sleep_between_calls_s: float = float(os.getenv("SLEEP_BETWEEN_CALLS_S", "3"))

    @staticmethod
    def from_env() -> "SiegConfig":
        api_key = os.getenv("SIEG_API_KEY")
        url_root = os.getenv("URL_BAIXAR_XMLS", "https://api.sieg.com")
        if not api_key:
            raise ValueError("API_KEY ausente do ambiente.")
        base_url = f"{url_root}//BaixarXmlsV2"
        return SiegConfig(api_key=api_key, base_url=base_url)


class SiegClient:
    
    def __init__(self, cfg: SiegConfig, session: Optional[Session] = None) -> None:
        self.cfg = cfg

        self.session = session or requests.Session()
        retry = Retry(
            total=3, backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("POST",)
        )
        adapter = HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # boto3 client com pool maior
        self.s3 = boto3.client(
            "s3",
            region_name=os.getenv("S3_REGION", "us-east-1"),
            config=BotoCfg(max_pool_connections=64, retries={"max_attempts": 3})
        )

        self.parser = DocumentoFiscalParser()

    @classmethod
    def from_env(cls, session: Optional[Session] = None) -> "SiegClient":
        return cls(SiegConfig.from_env(), session=session)

    def _post_json(self, payload: Dict) -> Optional[object]:
        url = f"{self.cfg.base_url}?api_key={self.cfg.api_key}"
        try:
            resp: Response = self.session.post(url, json=payload, timeout=self.cfg.timeout_s)
            resp.raise_for_status()
            return resp.json()  # não força isinstance aqui
        except requests.RequestException as e:
            logger.error("HTTP falhou: %s", e)
            return None

    @staticmethod
    def _payload_padrao(
        *,
        xml_type: XmlType,
        take: int,
        skip: int,
        start: datetime,
        end: datetime,
        include_events: bool,
        cnpj_cpf_emit: Optional[str],
    ) -> Dict:
        payload = {
            "XmlType": int(xml_type),
            "Take": int(take),
            "Skip": int(skip),
            "DataEmissaoInicio": start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            "DataEmissaoFim": end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            "Downloadevent": bool(include_events),
        }
        if cnpj_cpf_emit:
            payload["CnpjEmit"] = _only_digits(cnpj_cpf_emit)
        return payload

    @staticmethod
    def _payload_nfse(
        *,
        take: int,
        skip: int,
        start: datetime,
        end: datetime,
        cnpj_cpf_emit: Optional[str],
    ) -> Dict:
        payload = {
            "XmlType": int(XmlType.NFSE),
            "Take": int(take),
            "Skip": int(skip),
            "DataEmissaoInicio": start.strftime("%Y-%m-%d"),
            "DataEmissaoFim": end.strftime("%Y-%m-%d"),
        }
        if cnpj_cpf_emit:
            payload["CnpjEmit"] = _only_digits(cnpj_cpf_emit)
        return payload

    def _iter_batches(
        self,
        *,
        xml_type: XmlType,
        start: datetime,
        end: datetime,
        include_events: bool,
        cnpj_cpf_emit: Optional[str],
    ) -> Iterator[List[str]]:
        skip = 0
        min_gap = float(self.cfg.sleep_between_calls_s)  # ex.: 3.0
        last_call_ts = None  # controla intervalo entre chamadas da API

        while True:
            if xml_type == XmlType.NFSE:
                payload = self._payload_nfse(
                    take=self.cfg.take, skip=skip, start=start, end=end, cnpj_cpf_emit=cnpj_cpf_emit
                )
            else:
                payload = self._payload_padrao(
                    xml_type=xml_type,
                    take=self.cfg.take,
                    skip=skip,
                    start=start,
                    end=end,
                    include_events=include_events,
                    cnpj_cpf_emit=cnpj_cpf_emit,
                )

            logger.info(
                "POST %s | tipo=%s | %s..%s | skip=%d | eventos=%s | emit=%s",
                self.cfg.base_url, xml_type.name, start, end, skip, include_events, cnpj_cpf_emit
            )

            # --- RATE LIMIT: dormir apenas o necessário para garantir min_gap ---
            now = time.monotonic()
            if last_call_ts is not None:
                elapsed = now - last_call_ts
                if elapsed < min_gap:
                    time.sleep(min_gap - elapsed)
            # -------------------------------------------------------------------

            # chamada da API
            call_start = time.monotonic()
            raw_data = self._post_json(payload)
            last_call_ts = call_start  # marca o instante da chamada anterior

            if not raw_data or not isinstance(raw_data, dict) or not raw_data.get("xmls"):
                break

            if isinstance(raw_data["xmls"], str):
                try:
                    data = json.loads(raw_data["xmls"])
                except Exception as e:
                    logger.error("Erro parse JSON: %s", e)
                    break
            else:
                data = raw_data["xmls"]

            if not isinstance(data, list):
                logger.warning("Formato inesperado de dados: %s", type(data).__name__)
                break

            recebidos = len(data)
            yield data

            if recebidos < self.cfg.take:
                break
            skip += recebidos


    def _parse_item(self, item_b64: str) -> Optional[Tuple[str, str, str, str]]:
        try:
            xml_text = base64.b64decode(item_b64).decode("utf-8")
        except Exception as e:
            logger.warning("Falha base64: %s", e)
            return None

        r = self.parser.parse_documento_fiscal_string(xml_text)
        if not isinstance(r, dict) or "erro" in r:
            return None

        chave = r.get("chave_acesso")
        cnpj_emit = r.get("cnpj_emitente") or r.get("cnpj") or r.get("cpf_emitente")
        data_emissao = r.get("data_evento") if r.get("isevent") == "1" else r.get("data_emissao")

        if not (chave and cnpj_emit and data_emissao):
            return None

        data_emissao = data_emissao[:10]
        if r.get("isevent") == "1":
            file_name = f"{chave}_{r.get('tipo_documento')}_{r.get('tipo_evento')}_{r.get('sequencia_evento')}.xml"
        else:
            file_name = f"{chave}_{r.get('tipo_documento')}.xml"

        return xml_text, cnpj_emit, data_emissao, file_name

    def _process_batch(self, batch: Sequence[str], bucket: str) -> Tuple[int, int]:
        recebidos = len(batch)
        importados = 0
        for item in batch:
            meta = self._parse_item(item)
            if not meta:
                continue
            xml_text, cnpj_emit, data_emissao, file_name = meta
            ok = upload_string_to_s3(
                bucket_name=bucket,
                content=xml_text,
                cnpj_emit=cnpj_emit,
                data_emissao=data_emissao,
                file_name=file_name,
                s3_client=self.s3
            )
            if ok:
                importados += 1
        return recebidos, importados

    def download_por_emissao(
        self,
        *,
        start_date: datetime,
        end_date: datetime,
        xml_types: Sequence[XmlType] = (XmlType.NFE, XmlType.CTE, XmlType.NFCE, XmlType.CFE),
        include_events: bool = False,
        cnpj_cpf_emit: Optional[str] = None,
    ) -> None:
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise EnvironmentError("❌ Variável de ambiente S3_BUCKET não definida.")

        dia = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

        while dia <= fim:
            jan_ini = dia
            jan_fim = dia.replace(hour=23, minute=59, second=59, microsecond=0)
            total_r = total_i = 0

            for t in xml_types:
                for batch in self._iter_batches(
                    xml_type=t,
                    start=jan_ini,
                    end=jan_fim,
                    include_events=include_events,
                    cnpj_cpf_emit=cnpj_cpf_emit,
                ):
                    r, i = self._process_batch(batch, bucket)
                    total_r += r
                    total_i += i

            logger.info(
                "Dia %s concluído: recebidos=%d importados=%d",
                dia.strftime("%Y-%m-%d"), total_r, total_i
            )
            dia = dia + timedelta(days=1)

    def download_nfse_por_emissao(
        self,
        *,
        start_date: datetime,
        end_date: datetime,
        cnpj_cpf_emit: Optional[str] = None,
    ) -> None:
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise EnvironmentError("❌ Variável de ambiente S3_BUCKET não definida.")

        for batch in self._iter_batches(
            xml_type=XmlType.NFSE,
            start=start_date,
            end=end_date,
            include_events=False,
            cnpj_cpf_emit=cnpj_cpf_emit,
        ):
            self._process_batch(batch, bucket)


    @staticmethod
    def _month_range(year: int, month: int) -> Tuple[datetime, datetime]:
        """Retorna o intervalo [início, fim] (inclusive) do mês em UTC."""
        start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        if month == 12:
            next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        end = next_month - timedelta(seconds=1)
        return start, end

    @staticmethod
    def _pg_conn_from_env():
        """
        Conecta no Postgres usando variáveis de ambiente padrão:
        PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
        """
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DB_NAME"),
        )
        conn.autocommit = True
        return conn


    @staticmethod
    def _iter_empresas(conn: psycopg2.Connection) -> Iterable[Tuple[int, str]]:
        """
        Retorna (sk_empresa, cnpj_cpf) apenas de empresas ativas e não deletadas.
        Opcional: filtra certificados vencidos (mantido aqui).
        """
        sql = f"""
            SELECT sk_empresa, cnpj_cpf
            FROM bronze.empresas_clientes
            WHERE COALESCE(ativo, FALSE) = TRUE
            AND COALESCE(deletado, FALSE) = FALSE
            AND (data_expira IS NULL OR data_expira >= NOW())
            AND cnpj_cpf IS NOT NULL
            ORDER BY sk_empresa
        """
        with conn.cursor() as cur:
            cur.execute(sql)
            for row in cur:
                yield row  # (sk_empresa, cnpj_cpf)

    def baixar_xmls_por_mes(
        self,
        *,
        year: int,
        month: int,
        incluir_eventos: bool = False,
        xml_types: Iterable[XmlType] = (XmlType.NFE, XmlType.CTE, XmlType.NFCE, XmlType.CFE),
    ) -> None:
        """
        Lê empresas do DW e baixa XMLs da SIEG para o período (ano/mês).
        Usa credenciais SIEG/S3 do ambiente e Postgres via variáveis já configuradas.
        """
        # Usa a função utilitária definida na classe sem binding de 'self'
        inicio, fim = SiegClient._month_range(year, month)
        logger.info("Período-alvo: %s a %s (UTC)", inicio.isoformat(), fim.isoformat())

        # Conexão ao Postgres (método definido na classe sem 'self' na assinatura)
        conn = SiegClient._pg_conn_from_env()

        total_emp = 0
        try:
            # Itera empresas (método definido na classe sem 'self' na assinatura)
            for sk, cnpj in SiegClient._iter_empresas(conn):
                total_emp += 1
                logger.info("Empresa sk=%s | cnpj=%s | download %02d/%04d", sk, cnpj, month, year)

                # Usa a instância atual (self) para baixar e enviar ao S3
                self.download_por_emissao(
                    start_date=inicio,
                    end_date=fim,
                    xml_types=xml_types,
                    include_events=incluir_eventos,
                    cnpj_cpf_emit=cnpj,
                )

            logger.info("Processo concluído. Empresas processadas: %d", total_emp)
        finally:
            conn.close()



# -------------------- Exemplo de uso --------------------
if __name__ == "__main__":
    """
    Exemplo simples: baixar NFe/CTe/NFCe/CFe no mês inteiro,
    incluindo eventos, filtrando por emitente (opcional).
    """
    # Opcional: silenciar console mas manter arquivo (LOG_SILENT=1 já faz isso globalmente)
    logging.getLogger().handlers[0].setLevel(logging.CRITICAL)

    client = SiegClient.from_env()

    # Exemplo 1: mês/ano completos para NFE
    client.baixar_xmls_por_mes(
        year=2025,
        month=5,
        incluir_eventos=False,
        xml_types=[XmlType.NFE],  # pode incluir outros tipos
    )

    # Exemplo 2: intervalo arbitrário por emissão (se preferir rodar direto)
    # inicio = datetime(2025, 5, 25, tzinfo=timezone.utc)
    # fim = datetime(2025, 5, 30, tzinfo=timezone.utc)
    # client.download_por_emissao(start_date=inicio, 
    #                             end_date=fim, 
    #                             xml_types=[XmlType.NFE], 
    #                             cnpj_cpf_emit="24670826000126")
