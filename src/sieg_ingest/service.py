from __future__ import annotations
import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence, Optional, Tuple
from .config import SiegConfig
from .types import XmlType
from .api import SiegApi
from .batching import BatchIterator
from .parser_adapter import XmlParserAdapter
from .storage import S3Storage
from .repository import CompanyRepository

log = logging.getLogger(__name__)

class SiegIngestionService:
    def __init__(self, cfg: SiegConfig):
        self.cfg = cfg
        self.api = SiegApi(cfg)
        self.batcher = BatchIterator(cfg, self.api)
        self.parser = XmlParserAdapter()
        self.storage = S3Storage(cfg=cfg.s3)

    @staticmethod
    def month_range(
        year: int,
        month: int,
        tz: timezone = timezone.utc,
        limit_to_today: bool = False,
    ) -> Tuple[datetime, datetime]:
        """
        Retorna (início, fim) do mês no fuso informado.
        Se limit_to_today=True e (year, month) == mês atual no fuso, limita o fim a 23:59:59 do dia atual.
        """
        start = datetime(year, month, 1, tzinfo=tz)

        # primeiro dia do próximo mês
        next_month_start = (
            datetime(year + 1, 1, 1, tzinfo=tz)
            if month == 12
            else datetime(year, month + 1, 1, tzinfo=tz)
        )
        end = next_month_start - timedelta(seconds=1)

        if limit_to_today:
            now = datetime.now(tz)
            if now.year == year and now.month == month:
                today_start = datetime(year, month, now.day, tzinfo=tz)
                tomorrow_start = today_start + timedelta(days=1)
                end_today = tomorrow_start - timedelta(seconds=1)
                if end_today < end:
                    end = end_today

        return start, end

    def _process_batch(self, batch: Sequence[str]) -> Tuple[int,int]:
        rec = len(batch); imp = 0
        for item in batch:
            meta = self.parser.parse_item_b64(item)
            if not meta: continue
            xml_text, cnpj, data, fname = meta
            if self.storage.upload_parsed(xml_text, cnpj, data, fname):
                imp += 1
        return rec, imp

    def download_por_emissao(self, *, start_date: datetime, end_date: datetime,
                             xml_types: Sequence[XmlType]=(XmlType.NFE, XmlType.CTE, XmlType.NFCE, XmlType.CFE, XmlType.MDFE),
                             include_events: bool=False,
                             cnpj_emit: Optional[str]=None, cnpj_dest: Optional[str]=None) -> None:
        dia = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        while dia <= fim:
            jan_ini = dia
            jan_fim = dia.replace(hour=23, minute=59, second=59, microsecond=0)
            tot_r = tot_i = 0
            for t in xml_types:
                for batch in self.batcher.iter_batches(
                    xml_type=t, start=jan_ini, end=jan_fim, include_events=include_events,
                    cnpj_emit=cnpj_emit, cnpj_dest=cnpj_dest
                ):
                    r,i = self._process_batch(batch)
                    tot_r += r; tot_i += i
            log.info("Dia %s: recebidos=%d importados=%d", dia.date(), tot_r, tot_i)
            dia += timedelta(days=1)

    def download_nfse_por_emissao(self, *, start_date: datetime, end_date: datetime,
                                  cnpj_emit: Optional[str]=None, cnpj_dest: Optional[str]=None)->None:
        for batch in self.batcher.iter_batches(
            xml_type=XmlType.NFSE, start=start_date, end=end_date,
            include_events=False, cnpj_emit=cnpj_emit, cnpj_dest=cnpj_dest
        ):
            self._process_batch(batch)

    def download_por_participante(self, *, start_date: datetime, end_date: datetime,
                                  xml_types: Sequence[XmlType]=(XmlType.NFE, XmlType.CTE, XmlType.NFCE, XmlType.CFE, XmlType.MDFE),
                                  include_events: bool=False, cnpj: Optional[str]=None,
                                  participante: str="ambos", incluir_dest_quando_emitente: bool=False)->None:
        if not cnpj:
            self.download_por_emissao(start_date=start_date, end_date=end_date,
                                      xml_types=xml_types, include_events=include_events)
            return
        p = (participante or "ambos").lower()
        if p == "emitente":
            self.download_por_emissao(start_date=start_date, end_date=end_date,
                                      xml_types=xml_types, include_events=include_events, cnpj_emit=cnpj)
            if incluir_dest_quando_emitente:
                self.download_por_emissao(start_date=start_date, end_date=end_date,
                                          xml_types=xml_types, include_events=include_events, cnpj_dest=cnpj)
            return
        if p == "destinatario":
            self.download_por_emissao(start_date=start_date, end_date=end_date,
                                      xml_types=xml_types, include_events=include_events, cnpj_dest=cnpj)
            return
        self.download_por_emissao(start_date=start_date, end_date=end_date,
                                  xml_types=xml_types, include_events=include_events, cnpj_emit=cnpj)
        self.download_por_emissao(start_date=start_date, end_date=end_date,
                                  xml_types=xml_types, include_events=include_events, cnpj_dest=cnpj)

    def baixar_por_cnpj_ano_mes(self, *, cnpj: str, year: int, month: int,
                                incluir_eventos: bool=False,
                                xml_types: Iterable[XmlType]=(XmlType.NFE, XmlType.CTE, XmlType.NFCE, XmlType.CFE, XmlType.MDFE),
                                participante: str="ambos", incluir_dest_quando_emitente: bool=False,
                                tz=timezone.utc)->None:
        ini, fim = self.month_range(year, month, tz, limit_to_today=True)
        self.download_por_participante(start_date=ini, end_date=fim,
            xml_types=tuple(xml_types), include_events=incluir_eventos, cnpj=cnpj,
            participante=participante, incluir_dest_quando_emitente=incluir_dest_quando_emitente)

    def baixar_intervalo_dias(self, *, days_back: int=1,
                              xml_types: Sequence[XmlType]=(XmlType.NFE, XmlType.CTE, XmlType.NFCE, XmlType.CFE, XmlType.MDFE),
                              include_events: bool=False, cnpj: Optional[str]=None,
                              participante: str="ambos", incluir_dest_quando_emitente: bool=False,
                              tz=timezone.utc)->None:
        end = datetime.now(tz=tz).replace(hour=23, minute=59, second=59, microsecond=0)
        start = (end - timedelta(days=days_back-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if cnpj:
            self.download_por_participante(start_date=start, end_date=end,
                xml_types=xml_types, include_events=include_events, cnpj=cnpj,
                participante=participante, incluir_dest_quando_emitente=incluir_dest_quando_emitente)
        else:
            conn = CompanyRepository.connect_from_env()
            try:
                for _sk, cnpj_row in CompanyRepository.iter_empresas(conn):
                    self.download_por_participante(start_date=start, end_date=end,
                        xml_types=xml_types, include_events=include_events, cnpj=cnpj_row,
                        participante=participante, incluir_dest_quando_emitente=incluir_dest_quando_emitente)
            finally:
                conn.close()
