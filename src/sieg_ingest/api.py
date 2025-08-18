# sieg_ingest/api.py
from __future__ import annotations

import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sieg_ingest.config import SiegConfig  # usar a sua classe existente

log = logging.getLogger(__name__)

class SiegEndpoints:
    BAIXAR_XMLS_V2 = "BaixarXmlsV2"

def _smart_join(base_url: str, endpoint: str) -> str:
    """
    Junta base + endpoint sem duplicar e sem mexer em querystring.
    Aceita base com ou sem barra final; endpoint com ou sem barra inicial.
    """
    base = (base_url or "").rstrip("/")
    ep = (endpoint or "").lstrip("/")
    # se a base já termina com o endpoint, não duplica
    if base.endswith("/" + ep) or base.split("/")[-1] == ep:
        return base
    return urljoin(base + "/", ep)

class SiegApi:
    """
    Cliente HTTP para a SIEG.
    - Usa SiegConfig (api_key, base_url, timeout).
    - POST para recuperar XMLs em base64.
    """
    def __init__(self, cfg: SiegConfig, session: Optional[requests.Session] = None) -> None:
        self.cfg = cfg
        self.session = session or requests.Session()

        retry = Retry(
            total=3,
            backoff_factor=0.6,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("POST",),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "comapaxmls/1.0",
        })

    def post(self, payload: Dict[str, Any], endpoint: str = SiegEndpoints.BAIXAR_XMLS_V2) -> Optional[Dict[str, Any]]:
        """
        Executa POST na SIEG e normaliza o retorno.
        Retorna:
          - dict: {"xmls": [...]} quando a API devolve list
          - dict: resposta original quando a API devolve objeto
          - None: em erro de rede, 404/5xx, ou resposta não-JSON
        """
        # Monta a URL final sem encodar/modificar a api_key
        base_ep = _smart_join(self.cfg.base_url, endpoint)
        sep = "&" if "?" in base_ep else "?"
        url_final = f"{base_ep}{sep}api_key={self.cfg.api_key}"
        url1 = f"{self.cfg.base_url}/{endpoint}?api_key={self.cfg.api_key}"

        safe_url = url_final.replace(self.cfg.api_key, "******")
        log.debug("POST %s", safe_url)
        log.debug("Payload: %s", payload)

        try:
            resp: Response = self.session.post(url_final, json=payload, timeout=self.cfg.timeout_s)
        except requests.RequestException as e:
            log.error("Falha de rede ao chamar SIEG: %s", e)
            return None

        if resp.status_code == 404:
            log.error("SIEG 404 (endpoint/rota inválida?): %s", safe_url)
            return None
        if resp.status_code >= 500:
            log.error("SIEG %s: corpo=%s", resp.status_code, resp.text[:500])
            return None

        try:
            data = resp.json()
        except ValueError:
            log.error("Resposta não-JSON da SIEG: %s", resp.text[:500])
            return None

        if isinstance(data, list):
            return {"xmls": data}
        if isinstance(data, dict):
            return data

        log.warning("Formato inesperado da SIEG: %s", type(data).__name__)
        return None


def teste():
    import requests
    import json

    url = "https://api.sieg.com/BaixarXmlsV2?api_key="

    payload = json.dumps({
    "XmlType": 1,
    "Take": 50,
    "Skip": 0,
    "DataEmissaoInicio": "2025-08-15T00:00:00.000Z",
    "DataEmissaoFim": "2025-08-17T23:59:59.999Z",
    "Downloadevent": True
    })
    headers = {
    'Content-Type': 'application/json',
    'Cookie': 'AWSALB=DWcKSomwOB7w3LdM/Do9i+voPUXx1bIES8JkgAB2/M64nAHBMZLOftR0z2hq8109KezYcoseUj4B+58v/uPMw3QrdbPAZ90HwAfWCmT7QHYJvSlgkc3/18iaR3Do; AWSALBCORS=DWcKSomwOB7w3LdM/Do9i+voPUXx1bIES8JkgAB2/M64nAHBMZLOftR0z2hq8109KezYcoseUj4B+58v/uPMw3QrdbPAZ90HwAfWCmT7QHYJvSlgkc3/18iaR3Do; AWSALBTG=pOLSDcAwpCORV/2HNiEIolbuDR9FIW1dCUkLmBP5JQURtM9IBMAdPw4VvcBnJG/4MntXWFTCSq/ImdOIJtSbR5s0p+cVKWpKuTUmSqX5FyRjlKsHjj5/cUfN+qA8dDjoXCs84XgaunzjzEptr2xKvnRB1xWFOAhaxIXBcrOjYm1DjXrtSb4=; AWSALBTGCORS=pOLSDcAwpCORV/2HNiEIolbuDR9FIW1dCUkLmBP5JQURtM9IBMAdPw4VvcBnJG/4MntXWFTCSq/ImdOIJtSbR5s0p+cVKWpKuTUmSqX5FyRjlKsHjj5/cUfN+qA8dDjoXCs84XgaunzjzEptr2xKvnRB1xWFOAhaxIXBcrOjYm1DjXrtSb4='
    }

    #response = requests.request("POST", url, headers=headers, data=payload)
    #print(response.text)

    #        url1 = f"{self.cfg.base_url}/{endpoint}?api_key={self.cfg.api_key}"

    SiegApi(cfg=SiegConfig.from_env()).post(
        payload={
            "XmlType": 1,
            "Take": 50,
            "Skip": 0,
            "DataEmissaoInicio": "2025-08-15T00:00:00.000Z",
            "DataEmissaoFim": "2025-08-17T23:59:59.999Z",
            "Downloadevent": True
        },
        endpoint=SiegEndpoints.BAIXAR_XMLS_V2
    )


    

if __name__ == "__main__":
    teste()