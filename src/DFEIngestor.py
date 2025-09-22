import os
import io
import re
import csv
import boto3
import psycopg2
import logging
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterator, List, Tuple, Dict, Any, Optional
from psycopg2.extensions import connection as _PGConn
from dfe.DocumentoFiscalParser import DocumentoFiscalParser
from dotenv import load_dotenv
from botocore.config import Config
from botocore.exceptions import ClientError

# ===================== .env =====================
# Caminho absoluto para o .env na raiz do projeto
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=os.path.abspath(env_path))

# ===================== Logging =====================
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ===================== Utils =====================
_DIGITS = re.compile(r"\D+")

def only_digits(v: Optional[str]) -> str:
    return "" if not v else _DIGITS.sub("", v)

def is_cnpj_cpf(s: str) -> bool:
    # 11 (CPF) ou 14 (CNPJ)
    return s.isdigit() and len(s) in (11, 14)

def parse_iso_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)

# ===================== Classe Principal =====================
class DFEIngestor:
    """
    Layout esperado no S3:
      s3://<bucket>/documentos/<CNPJ_EMITENTE>/<AAAA>/<MM>/.../*.xml

    Estratégia:
      1) Processa DF-e **emitidos por clientes** (leitura da tabela bronze.empresas_clientes).
      2) Processa DF-e **emitidos por não-clientes** (descobre <CNPJ> no 1º nível após 'documentos/').
      - Filtro temporal por LastModified (janela relativa via S3_ONLY_LAST_HOURS ou intervalo START/END).
      - GET+parse concorrente (I/O-bound).
      - Dedup em memória no lote + INSERT ... ON CONFLICT (idempotente).
      - COPY em tabelas temporárias **sem constraints** por desempenho e para suportar múltiplos eventos por chave.
    """

    # ---------- Init ----------
    def __init__(self) -> None:
        # S3
        self.bucket = os.environ.get("S3_BUCKET")
        if not self.bucket:
            raise ValueError("S3_BUCKET não definido.")
        self.prefix_base = os.environ.get("DEFAULT_PREFIX", "documentos/")
        if not self.prefix_base.endswith("/"):
            self.prefix_base += "/"

        self.s3 = boto3.client(
            "s3",
            config=Config(
                retries={"max_attempts": int(os.getenv("AWS_RETRY_ATTEMPTS", "10")), "mode": "standard"},
                connect_timeout=10,
                read_timeout=60,
                tcp_keepalive=True,
            )
        )

        # Parser
        self.parser = DocumentoFiscalParser()

        # Postgres
        self.conn: _PGConn = psycopg2.connect(
            host=os.environ.get("DB_HOST"),
            port=int(os.environ.get("DB_PORT", "5432")),
            database=os.environ.get("DB_NAME"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            connect_timeout=10,
        )
        self.conn.autocommit = False
        with self.conn.cursor() as cur:
            cur.execute("SET statement_timeout = %s;", (os.getenv("PG_STMT_TIMEOUT_MS", "60000"),))

        # Desempenho
        self.batch_size = int(os.environ.get("BULK_BATCH_SIZE", "2000"))
        self.max_workers = int(os.environ.get("MAX_WORKERS", "8"))
        self.include_non_client_emitters = (os.environ.get("INCLUDE_NON_CLIENT_EMITTERS", "true").lower() == "true")

        # Janela temporal
        self.start_dt, self.end_dt, self.since_utc = self._resolve_janela_tempo()

    # ---------- Janela Temporal ----------
    def _resolve_janela_tempo(self) -> tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
        sd = os.environ.get("START_DATE")
        ed = os.environ.get("END_DATE")
        if sd and ed:
            start_dt = parse_iso_dt(sd)
            end_dt = parse_iso_dt(ed)
            if start_dt >= end_dt:
                raise ValueError("START_DATE deve ser < END_DATE.")
            logger.info("Intervalo explícito: %s -> %s", start_dt.isoformat(), end_dt.isoformat())
            return start_dt, end_dt, None

        hours = int(os.getenv("S3_ONLY_LAST_HOURS", "24"))
        if hours > 0:
            since_utc = datetime.now(timezone.utc) - timedelta(hours=hours)
            logger.info("Janela relativa: últimas %dh (desde %s)", hours, since_utc.isoformat())
            return None, None, since_utc

        logger.info("Sem janela (varredura completa).")
        return None, None, None

    # ---------- Clientes ----------
    def _fetch_clientes(self) -> list[str]:
        """
        Retorna lista de CNPJ/CPF (somente dígitos) dos clientes ativos (não deletados).
        """
        sql = """
            SELECT cnpj_cpf
            FROM bronze.empresas_clientes
            WHERE (ativo IS TRUE OR ativo IS NULL)
              AND (deletado IS DISTINCT FROM TRUE)
        """
        with self.conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        clientes = [only_digits(r[0]) for r in rows if only_digits(r[0])]
        logger.info("Clientes ativos carregados: %d", len(clientes))
        return clientes

    # ---------- Emitentes no bucket (não-clientes) ----------
    def _listar_emitentes_no_bucket(self) -> list[str]:
        """
        Descobre CNPJs/CPFs de emitentes pelo 1º nível:
          Prefix = 'documentos/', Delimiter='/'  => CommonPrefixes = ['documentos/<cnpj>/', ...]
        Essa chamada **não** desce para <AAAA>/<MM>; é barata e escalável.
        """
        emitentes: list[str] = []
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(
            Bucket=self.bucket,
            Prefix=self.prefix_base,
            Delimiter="/"
        ):
            for cp in page.get("CommonPrefixes", []):
                pfx: str = cp.get("Prefix", "")
                token = pfx[len(self.prefix_base):].strip("/")
                token_digits = only_digits(token)
                if is_cnpj_cpf(token_digits):
                    emitentes.append(token_digits)
        # remover duplicatas preservando ordem
        seen = set()
        unique_emitentes = []
        for e in emitentes:
            if e not in seen:
                seen.add(e)
                unique_emitentes.append(e)
        logger.info("Emitentes (nível 1) encontrados no bucket: %d", len(unique_emitentes))
        return unique_emitentes

    # ---------- Listagem S3 ----------
    def _iterar_xmls_s3(
        self,
        prefix: str,
        since_utc: Optional[datetime],
        start_dt: Optional[datetime],
        end_dt: Optional[datetime],
    ) -> Iterator[Tuple[str, datetime]]:
        """
        Lista .xml paginando sob um prefix arbitrário (ex.: documentos/<cnpj>/),
        filtrando por LastModified conforme janela/intervalo.
        OBS: Não precisamos navegar <AAAA>/<MM> manualmente; o paginator percorre recursivamente.
        """
        paginator = self.s3.get_paginator("list_objects_v2")
        try:
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    key = obj.get("Key", "")
                    if not key.lower().endswith(".xml"):
                        continue
                    lm: datetime = obj.get("LastModified")
                    if since_utc and lm < since_utc:
                        continue
                    if start_dt and end_dt and (lm < start_dt or lm > end_dt):
                        continue
                    yield key, lm
        except ClientError as e:
            logger.error("Erro ao paginar S3 em %s: %s", prefix, e, exc_info=True)

    # ---------- Parse ----------
    def _baixar_e_parsear(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            s3_obj = self.s3.get_object(Bucket=self.bucket, Key=key)
            xml_content = s3_obj["Body"].read().decode("utf-8", errors="ignore")
            result = self.parser.parse_documento_fiscal_string(xml_content)
            if "erro" in result:
                logger.warning("Parser falhou: %s -> %s", key, result["erro"])
                return None
            result["_s3_uri"] = f"s3://{self.bucket}/{key}"
            return result
        except ClientError as e:
            logger.error("Falha S3 %s: %s", key, e, exc_info=True)
            return None
        except Exception as e:
            logger.error("Falha parse %s: %s", key, e, exc_info=True)
            return None

    # ---------- COPY helpers ----------
    @staticmethod
    def _to_field(val: Any) -> str:
        if val is None:
            return ""
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val)

    def _copy_docs(self, rows: List[Tuple]) -> None:
        if not rows:
            return
        buf = io.StringIO()
        w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow([self._to_field(x) for x in r])
        buf.seek(0)
        with self.conn.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS tmp_identificacao_dfe;
                CREATE TEMP TABLE tmp_identificacao_dfe
                (LIKE bronze.identificacao_dfe INCLUDING DEFAULTS)
                ON COMMIT DROP;
            """)
            cur.copy_expert("""
                COPY tmp_identificacao_dfe (
                    cnpjcpf_emitente, cnpjcpf_destinatario, data_emissao,
                    chave_acesso, tipo_documento, endereco_s3
                )
                FROM STDIN WITH (FORMAT CSV, QUOTE '"', ESCAPE '"', DELIMITER ',', NULL '');
            """, buf)
            cur.execute("""
                INSERT INTO bronze.identificacao_dfe AS d (
                    cnpjcpf_emitente, cnpjcpf_destinatario, data_emissao,
                    chave_acesso, tipo_documento, endereco_s3
                )
                SELECT
                    t.cnpjcpf_emitente, t.cnpjcpf_destinatario, t.data_emissao,
                    t.chave_acesso, t.tipo_documento, t.endereco_s3
                FROM tmp_identificacao_dfe t
                ON CONFLICT (chave_acesso) DO NOTHING;
            """)

    def _copy_eventos(self, rows: List[Tuple]) -> None:
        if not rows:
            return
        buf = io.StringIO()
        w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            w.writerow([self._to_field(x) for x in r])
        buf.seek(0)
        with self.conn.cursor() as cur:
            cur.execute("""
                DROP TABLE IF EXISTS tmp_evento_dfe;
                CREATE TEMP TABLE tmp_evento_dfe
                (LIKE bronze.evento_dfe INCLUDING DEFAULTS)
                ON COMMIT DROP;
            """)
            cur.copy_expert("""
                COPY tmp_evento_dfe (
                    chave_acesso, tipo_evento, descricao_evento, data_evento,
                    protocolo, cnpjcpf_emitente, endereco_s3
                )
                FROM STDIN WITH (FORMAT CSV, QUOTE '"', ESCAPE '"', DELIMITER ',', NULL '');
            """, buf)
            cur.execute("""
                INSERT INTO bronze.evento_dfe AS e (
                    chave_acesso, tipo_evento, descricao_evento, data_evento,
                    protocolo, cnpjcpf_emitente, endereco_s3
                )
                SELECT
                    t.chave_acesso, t.tipo_evento, t.descricao_evento, t.data_evento,
                    t.protocolo, t.cnpjcpf_emitente, t.endereco_s3
                FROM tmp_evento_dfe t
                ON CONFLICT DO NOTHING;
                -- Recomendado: UNIQUE (chave_acesso, tipo_evento, protocolo) na tabela final
            """)

    def _flush(self, docs_batch: List[Tuple], eventos_batch: List[Tuple]) -> None:
        try:
            self._copy_docs(docs_batch)
            self._copy_eventos(eventos_batch)
            self.conn.commit()
            logger.info("COPY ok: docs=%d eventos=%d", len(docs_batch), len(eventos_batch))
        except Exception as e:
            self.conn.rollback()
            logger.error("Erro COPY (rollback): %s", e, exc_info=True)

    # ---------- Núcleo genérico por prefixo ----------
    def _processar_por_prefixo(self, prefix: str, usar_filtros_tempo: bool = True) -> tuple[int, int]:
        docs_batch: List[Tuple] = []
        eventos_batch: List[Tuple] = []
        seen_docs: set[str] = set()
        seen_evt: set[Tuple[str, str, str]] = set()

        total_docs = total_eventos = 0

        since_utc = self.since_utc if usar_filtros_tempo else None
        start_dt = self.start_dt if usar_filtros_tempo else None
        end_dt = self.end_dt if usar_filtros_tempo else None

        keys = list(self._iterar_xmls_s3(prefix, since_utc, start_dt, end_dt))
        if not keys:
            logger.info("Nenhum DFE encontrado em %s", prefix)
            return 0, 0

        logger.info("Qtd DFE em %s: %d", prefix, len(keys))

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(self._baixar_e_parsear, k): k for k, _ in keys}
            for fut in as_completed(futures):
                data = fut.result()
                if not data:
                    continue

                chave = data.get("chave_acesso")
                if not chave:
                    continue

                cnpj_emit = only_digits(data.get("cnpj_emitente") or data.get("cpf_emitente"))
                # >>> ALTERAÇÃO AQUI: passa a considerar os novos campos do parser <<<
                cnpj_dest = only_digits(
                    data.get("cnpj_destinatario") or data.get("cpf_destinatario") or data.get("destinatario")
                )
                # <<< FIM DA ALTERAÇÃO >>>
                s3_uri = data.get("_s3_uri")
                tipo = (data.get("tipo_documento") or "").lower()

                if tipo.startswith("evento") or data.get("isevent") == "1":
                    te = data.get("tipo_evento") or ""
                    pr = data.get("protocolo") or ""
                    dk = (chave, te, pr)
                    if dk in seen_evt:
                        continue
                    seen_evt.add(dk)
                    eventos_batch.append((
                        chave, te, data.get("descricao_evento"),
                        data.get("data_evento"), pr,
                        cnpj_emit, s3_uri
                    ))
                else:
                    if chave in seen_docs:
                        continue
                    seen_docs.add(chave)
                    docs_batch.append((
                        cnpj_emit, cnpj_dest, data.get("data_emissao"),
                        chave, data.get("tipo_documento"), s3_uri
                    ))

                if (len(docs_batch) + len(eventos_batch)) >= self.batch_size:
                    self._flush(docs_batch, eventos_batch)
                    total_docs += len(docs_batch)
                    total_eventos += len(eventos_batch)
                    docs_batch.clear(); eventos_batch.clear()
                    seen_docs.clear(); seen_evt.clear()

        if docs_batch or eventos_batch:
            self._flush(docs_batch, eventos_batch)
            total_docs += len(docs_batch)
            total_eventos += len(eventos_batch)

        return total_docs, total_eventos

    # ---------- Núcleo por emitente ----------
    def _processar_emitidos_por_emitente(self, cnpj_emitente: str) -> tuple[int, int]:
        prefix = f"{self.prefix_base}{cnpj_emitente}/"
        return self._processar_por_prefixo(prefix, usar_filtros_tempo=True)

    # ---------- Modo pontual: 1 CNPJ + ano/mês ----------
    def ingerir_emitente_ano_mes(self, cnpj_emitente: str, ano: int, mes: int) -> tuple[int, int]:
        """
        Ingestão pontual de um emitente em um ano/mês específico.
        Ignora filtros de tempo por LastModified e lê todo o prefixo:
          documentos/<cnpj>/<ano>/<mes>/
        """
        cnpj = only_digits(cnpj_emitente)
        if not is_cnpj_cpf(cnpj):
            raise ValueError(f"CNPJ/CPF inválido: {cnpj_emitente}")

        if not (1 <= mes <= 12):
            raise ValueError("Mês deve estar entre 1 e 12")

        prefix = f"{self.prefix_base}{cnpj}/{ano}/{mes:02d}/"
        logger.info("Iniciando ingestão pontual: cnpj=%s ano=%d mes=%02d prefix=%s", cnpj, ano, mes, prefix)
        return self._processar_por_prefixo(prefix, usar_filtros_tempo=False)

    # ---------- NOVO: Modo mês/ano (todos os emitentes) ----------
    def ingerir_mes_ano(self, ano: int, mes: int, *, incluir_nao_clientes: Optional[bool] = None) -> tuple[int, int]:
        """
        Ingestão de **todo um mês/ano** para todos os emitentes.
        - Lê clientes (bronze.empresas_clientes)
        - Opcionalmente inclui emitentes não-clientes descobertos no bucket (nível 1 após prefixo).
        - Ignora filtros de tempo por LastModified (varredura completa do mês).
        - Caminho: documentos/<cnpj>/<ano>/<mes>/

        Retorna (total_docs, total_eventos).
        """
        if not (1 <= mes <= 12):
            raise ValueError("Mês deve estar entre 1 e 12")

        total_docs = total_eventos = 0

        clientes = self._fetch_clientes()
        emitentes: List[str] = list(clientes)
        clientes_set = set(clientes)

        use_non_clients = self.include_non_client_emitters if incluir_nao_clientes is None else incluir_nao_clientes
        if use_non_clients:
            bucket_emit = set(self._listar_emitentes_no_bucket())
            emitentes.extend([c for c in bucket_emit if c not in clientes_set])

        if not emitentes:
            logger.info("Nenhum emitente encontrado para ingerir mês/ano %04d/%02d.", ano, mes)
            return 0, 0

        logger.info("Iniciando ingestão mês/ano %04d/%02d para %d emitente(s).", ano, mes, len(emitentes))

        for cnpj in emitentes:
            prefix = f"{self.prefix_base}{cnpj}/{ano}/{mes:02d}/"
            d, e = self._processar_por_prefixo(prefix, usar_filtros_tempo=False)
            total_docs += d
            total_eventos += e
            logger.info("[MÊS/ANO %04d/%02d | %s] docs=%d eventos=%d", ano, mes, cnpj, d, e)

        logger.info("INGESTÃO %04d/%02d CONCLUÍDA -> docs=%d eventos=%d", ano, mes, total_docs, total_eventos)
        return total_docs, total_eventos

    # ---------- Orquestração ----------
    def executar(self) -> None:
        total_docs = total_eventos = 0

        try:
            # 1) Emitidos por clientes
            clientes = self._fetch_clientes()
            clientes_set = set(clientes)
            for cnpj in clientes:
                d, e = self._processar_emitidos_por_emitente(cnpj)
                total_docs += d; total_eventos += e
                logger.info("[CLIENTE %s] Emitidos -> docs=%d eventos=%d", cnpj, d, e)

            # 2) Emitidos por não-clientes (descobre no 1º nível após 'documentos/')
            if self.include_non_client_emitters:
                emitentes_bucket = set(self._listar_emitentes_no_bucket())
                nao_clientes = [c for c in emitentes_bucket if c not in clientes_set]
                logger.info("Emitentes não-clientes a processar: %d", len(nao_clientes))

                for cnpj in nao_clientes:
                    d, e = self._processar_emitidos_por_emitente(cnpj)
                    total_docs += d; total_eventos += e
                    logger.info("[NAO-CLIENTE %s] Emitidos -> docs=%d eventos=%d", cnpj, d, e)

            logger.info("TOTAL inseridos: docs=%d | eventos=%d", total_docs, total_eventos)

        finally:
            self.conn.close()

# ===================== Entrypoint =====================
def main():
    """
    Função principal para ingestão de Documentos Fiscais Eletrônicos (DF-e) via S3.
    Esta função permite a execução do processo de ingestão de DF-e de diferentes formas:
    1. Por meio de parâmetros de linha de comando (CNPJ, ano e mês), realiza a ingestão pontual de um emitente específico.
    2. Caso apenas ano e mês sejam informados, realiza a ingestão de todos os emitentes para o período especificado.
    3. Alternativamente, permite a configuração dos parâmetros via variáveis de ambiente (TARGET_CNPJ, TARGET_ANO, TARGET_MES).
    4. Se nenhum parâmetro for informado, executa o fluxo completo de ingestão, abrangendo clientes e não clientes em janelas de tempo.
    O objetivo é flexibilizar o processo de ingestão, permitindo execuções pontuais, por período ou completas, conforme a necessidade.
    """

    # Opcional: silenciar console mas manter arquivo (LOG_SILENT=1 já faz isso globalmente)
    logging.getLogger().handlers[0].setLevel(logging.CRITICAL)

    import argparse

    parser = argparse.ArgumentParser(description="Ingestão de DF-e via S3")
    parser.add_argument("--cnpj", help="CNPJ/CPF do emitente (apenas dígitos ou formatado)")
    parser.add_argument("--ano", type=int, help="Ano (YYYY)")
    parser.add_argument("--mes", type=int, help="Mês (1-12)")
    args = parser.parse_args()

    job = DFEIngestor()

    # Prioridade 1: parâmetros CLI
    if args.cnpj and args.ano and args.mes:
        d, e = job.ingerir_emitente_ano_mes(args.cnpj, args.ano, args.mes)
        logger.info("Ingestão pontual concluída -> docs=%d eventos=%d", d, e)
        return

    # NOVO: mês/ano para todos (sem CNPJ)
    if args.ano and args.mes and not args.cnpj:
        d, e = job.ingerir_mes_ano(args.ano, args.mes)
        logger.info("Ingestão mês/ano (todos) concluída -> docs=%d eventos=%d", d, e)
        return

    # 34.228.897/0001-27 | 34228897000127 | FERRAGENS LDA
    # 24.670.826/0001-26 | 24670826000126 | COMAPAR COMERCIO DE MAQUINAS E PECAS LTDA
    # 08.959.064/0001-26 | 08959064000126 | J B RECICLAGEM LTDA
    # 51.254.159/0001-73 | 51254159000173 | KARINA  PLASTICOS LTDA (Emitente contra J B Reciclagem)
    # 14.739.053/0005-67 | 14739053000567 | K R L LOPES DE CASTRO E CIA LTDA (Emitente contra J B Reciclagem)

    # Prioridade 2: variáveis de ambiente (TARGET_CNPJ, TARGET_ANO, TARGET_MES)
    #env_cnpj = '14739053000567'  # os.getenv("TARGET_CNPJ")
    env_cnpj = None              # os.getenv("TARGET_CNPJ")
    env_ano = '2025'             # os.getenv("TARGET_ANO")
    env_mes = '09'               # os.getenv("TARGET_MES")

    # if env_cnpj and env_ano and env_mes:
    #     d, e = job.ingerir_emitente_ano_mes(env_cnpj, int(env_ano), int(env_mes))
    #     logger.info("Ingestão pontual (ENV) concluída -> docs=%d eventos=%d", d, e)
    #     return

    # (Opcional) mês/ano via ENV sem CNPJ
    # Descomente as 3 linhas abaixo se quiser habilitar por ENV também:
    if not env_cnpj and env_ano and env_mes:
        d, e = job.ingerir_mes_ano(int(env_ano), int(env_mes))
        logger.info("Ingestão mês/ano (ENV, todos) concluída -> docs=%d eventos=%d", d, e); return

    # Fallback: fluxo completo (clientes + não clientes) com janelas de tempo
    job.executar()

if __name__ == "__main__":
    main()
# ===================== Fim =====================