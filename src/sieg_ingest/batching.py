from __future__ import annotations
import logging, json
from datetime import datetime
from typing import Iterator, List, Optional
from .types import XmlType
from .config import SiegConfig
from .api import SiegApi
from .ratelimit import RateLimiter
from .payloads import PayloadBuilder

log = logging.getLogger(__name__)

class BatchIterator:
    def __init__(self, cfg: SiegConfig, api: SiegApi) -> None:
        self.cfg = cfg
        self.api = api
        self.rl = RateLimiter(cfg.sleep_between_calls_s)

    def iter_batches(self, *, xml_type: XmlType, start: datetime, end: datetime,
                     include_events: bool, cnpj_emit: Optional[str], cnpj_dest: Optional[str]
    ) -> Iterator[List[str]]:
        skip = 0
        while True:
            # antes:
            # payload = (PayloadBuilder.nfse if xml_type == XmlType.NFSE else PayloadBuilder.padrao)(
            #     take=self.cfg.take, skip=skip, start=start, end=end,
            #     include_events=include_events if xml_type != XmlType.NFSE else False,
            #     cnpj_emit=cnpj_emit, cnpj_dest=cnpj_dest
            # )

            # depois (corrigido):
            if xml_type == XmlType.NFSE:
                payload = PayloadBuilder.nfse(
                    take=self.cfg.take,
                    skip=skip,
                    start=start,
                    end=end,
                    cnpj_emit=cnpj_emit,
                    cnpj_dest=cnpj_dest,
                )
            else:
                payload = PayloadBuilder.padrao(
                    xml_type=xml_type,                # <-- Faltava isso
                    take=self.cfg.take,
                    skip=skip,
                    start=start,
                    end=end,
                    include_events=include_events,    # <-- Só padrao aceita include_events
                    cnpj_emit=cnpj_emit,
                    cnpj_dest=cnpj_dest,
                )

            log.info("SIEG %s %s..%s skip=%d emit=%s dest=%s",
                     xml_type.name, start.isoformat(), end.isoformat(), skip, cnpj_emit, cnpj_dest)

            self.rl.wait()
            raw = self.api.post(payload)
            self.rl.mark()

            if not raw or "xmls" not in raw: break
            data = raw["xmls"]
            if isinstance(data, str):
                try: data = json.loads(data)
                except Exception as e:
                    log.error("Falha parse json xmls: %s", e); break

            if not isinstance(data, list) or not data: break
            yield data
            if len(data) < self.cfg.take: break
            skip += len(data)
