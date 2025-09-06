from __future__ import annotations
from typing import Dict, Any
import xml.etree.ElementTree as ET

from DFeNew.logger import get_logger
from DFeNew.utils import local_name
from DFeNew.types import ParseOut
from DFeNew.nfe_cte_mdfe import parse_nfe_cte_mdfe
from DFeNew.evento import parse_evento
from DFeNew.nfse import parse_nfse, looks_like_nfse

log = get_logger(__name__)

class DFeNew:
    """
    Fachada estável p/ DF-e.
    Mantém compatibilidade com o retorno da sua classe original (dict).
    Métodos:
      - parse_string(xml: str) -> Dict[str, Any]
      - parse_file(path: str, encoding="utf-8") -> Dict[str, Any]
    """

    def parse_string(self, xml: str) -> Dict[str, Any]:
        root = ET.fromstring(xml)
        return self._parse_root(root).asdict()

    def parse_file(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        with open(path, "r", encoding=encoding) as f:
            return self.parse_string(f.read())

    # núcleo
    def _parse_root(self, root: ET.Element) -> ParseOut:
        tag = local_name(root.tag)
        tipo_map = {
            "nfeproc": "NF-e", "nfe": "NF-e",
            "cteproc": "CT-e", "cte": "CT-e",
            "mdfeproc":"MDF-e","mdfe":"MDF-e",
            "comppnfse":"NFS-e","compnfse":"NFS-e","nfse":"NFS-e",
            "proceventonfe":"Evento","proceventocte":"Evento",
            "proceventomdfe":"Evento","eventoproc":"Evento","evento":"Evento",
        }
        tipo = tipo_map.get(tag)

        if tipo in {"NF-e","CT-e","MDF-e"}:
            return parse_nfe_cte_mdfe(root, tipo)
        if tipo == "Evento":
            return parse_evento(root)
        if tipo == "NFS-e" or looks_like_nfse(root):
            return parse_nfse(root)

        log.warning("Tipo de documento não identificado (tag='%s')", tag)
        return ParseOut()  # vazio, caller decide como tratar
