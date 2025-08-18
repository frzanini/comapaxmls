# tests/test_service.py
import base64
from pytest import MonkeyPatch
from sieg_ingest.config import SiegConfig
from sieg_ingest.service import SiegIngestionService
from sieg_ingest.types import XmlType

def test_payload_and_flow(monkeypatch):
    cfg = SiegConfig(api_key="dummy", base_url="http://example.invalid", take=10, timeout_s=5, sleep_between_calls_s=0.0)
    svc = SiegIngestionService(cfg)

    def fake_post(_): return {"xmls": [base64.b64encode(b"<xml/>").decode()]}
    monkeypatch.setattr(svc.api, "post", fake_post)

    def fake_parse(_b64): return "<xml/>", "12345678000199", "2025-08-16", "chave_NFE.xml"
    monkeypatch.setattr(svc.parser, "parse_item_b64", fake_parse)

    monkeypatch.setattr(svc.storage, "upload_parsed", lambda *a, **k: True)

    svc.download_por_emissao(
        start_date=__import__("datetime").datetime(2025,8,15),
        end_date=__import__("datetime").datetime(2025,8,15),
        xml_types=(XmlType.NFE,),
    )

if __name__ == "__main__":
    mp = MonkeyPatch()
    try:
        test_payload_and_flow(mp)
        print("Test completed successfully.")
    finally:
        mp.undo()
