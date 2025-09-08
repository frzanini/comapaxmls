from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import List, Sequence
from settings import Settings
from db_repository import DBRepository, Paper
from s3_client import S3Client
from DFeNewAdapter import DFeNewAdapter
from domain import NFeNota
from layouts import ANEXO04_SAIDAS, ANEXO07_C170, ANEXO09_ENTRADAS
from mappers import map_item_to_c170, map_nota_to_entradas, map_nota_to_saidas
from formatter import Formatter

class SciExporter:
    """Orquestra: DB -> S3 -> Parser -> TXT (SCI)."""
    def __init__(self, st: Settings) -> None:
        st.validate()
        self._st = st
        self._db = DBRepository(st)
        self._s3 = S3Client(region_name=st.aws_region)
        self._parser = DFeNewAdapter()

    def close(self) -> None:
        self._db.close()

    def _rows_anexo07(self, notas: List[NFeNota], who_cnpj: str):
        rows = []
        for n in notas:
            # normaliza antes de comparar
            dest = only_digits(n.cnpj_dest or "")
            tipo_mov = "E" if dest == who_cnpj else "S"
            for it in n.items or []:
                rows.append(map_item_to_c170(n, it, tipo_mov))
        return rows

    def _rows_anexo09(self, notas: List[NFeNota], who_cnpj: str):
        # ENTRADAS: somente notas cujo destinatário == who_cnpj
        filtradas = [n for n in notas if only_digits(n.cnpj_dest or "") == who_cnpj]
        return [map_nota_to_entradas(n, i + 1) for i, n in enumerate(filtradas)]

    def _rows_anexo04(self, notas: List[NFeNota], who_cnpj: str):
        # SAÍDAS: somente notas cujo emitente == who_cnpj
        filtradas = [n for n in notas if only_digits(n.cnpj_emit or "") == who_cnpj]
        return [map_nota_to_saidas(n, i + 1) for i, n in enumerate(filtradas)]


    def generate(self, cnpj: str, inicio: date, fim: date, papel: str, anexos: Sequence[str]) -> None:
        rows_db = self._db.list_s3_uris(cnpj, inicio, fim, papel)
        if not rows_db:
            return
        notas: List[NFeNota] = []
        for r in rows_db:
            xml = self._s3.get_text(r.s3_uri)
            n = self._parser.parse(xml)
            notas.append(n)
        base = self._st.output_dir / only_digits(cnpj) / f"{inicio.strftime('%Y%m%d')}-{fim.strftime('%Y%m%d')}"
        base.mkdir(parents=True, exist_ok=True)
        if "07" in anexos:
            Formatter.write_rows(base / "anexo07_c170.txt", ANEXO07_C170, self._rows_anexo07(notas, who_cnpj=only_digits(cnpj)))
        if "09" in anexos:
            Formatter.write_rows(base / "anexo09_entradas.txt", ANEXO09_ENTRADAS, self._rows_anexo09(notas, who_cnpj=only_digits(cnpj)))
        if "04" in anexos:
            Formatter.write_rows(base / "anexo04_saidas.txt", ANEXO04_SAIDAS, self._rows_anexo04(notas, who_cnpj=only_digits(cnpj)))

# helper local
from utils import only_digits