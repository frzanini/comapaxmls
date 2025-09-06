"""
Testes de integração para a fachada DFeNew.

Pré-requisito:
- O pacote DFeNew deve estar acessível no PYTHONPATH (ex.: estrutura "src/DFeNew/...").
- __init__.py deve exportar `DFeNew` (from .facade import DFeNew).

Execução:
- pytest -q
- ou: python tests/test_dfenew.py  (tem um __main__ que chama pytest com -v -rA)
"""

import pytest

# Importa a fachada renomeada
from DFeNew import DFeNew


@pytest.fixture(scope="module")
def dfe():
    return DFeNew()


# =========================
# Fixtures de XML (mocks)
# =========================

@pytest.fixture
def xml_nfe_minimo():
    # NFe em nfeProc com prot
    return """<?xml version="1.0" encoding="UTF-8"?>
    <nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
      <NFe>
        <infNFe Id="NFe35100123000000000000550010000000011000000012">
          <ide>
            <dhEmi>2025-09-04T10:00:00</dhEmi>
          </ide>
          <emit>
            <CNPJ>12345678000195</CNPJ>
          </emit>
          <dest>
            <CNPJ>98765432000188</CNPJ>
          </dest>
        </infNFe>
      </NFe>
      <protNFe>
        <infProt>
          <nProt>1234567890</nProt>
        </infProt>
      </protNFe>
    </nfeProc>
    """


@pytest.fixture
def xml_evento_minimo():
    # Evento de cancelamento (exemplo) em procEventoNFe
    return """<?xml version="1.0" encoding="UTF-8"?>
    <procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe">
      <evento>
        <infEvento>
          <chNFe>35100123000000000000550010000000011000000012</chNFe>
          <tpEvento>110111</tpEvento>
          <nSeqEvento>1</nSeqEvento>
          <CNPJ>12345678000195</CNPJ>
          <dhEvento>2025-09-04T15:00:00</dhEvento>
          <detEvento>
            <descEvento>Cancelamento</descEvento>
          </detEvento>
        </infEvento>
      </evento>
    </procEventoNFe>
    """


@pytest.fixture
def xml_nfse_minimo():
    # Variante ABRASF comum
    return """<?xml version="1.0" encoding="UTF-8"?>
    <CompNfse xmlns="http://www.abrasf.org.br/nfse.xsd">
      <Nfse>
        <InfNfse>
          <IdentificacaoNfse>
            <Numero>20250001</Numero>
          </IdentificacaoNfse>
          <DataEmissao>2025-09-04</DataEmissao>
        </InfNfse>
        <PrestadorServico>
          <IdentificacaoPrestador>
            <Cnpj>12345678000195</Cnpj>
          </IdentificacaoPrestador>
        </PrestadorServico>
        <TomadorServico>
          <IdentificacaoTomador>
            <CpfCnpj>
              <Cnpj>98765432000188</Cnpj>
            </CpfCnpj>
          </IdentificacaoTomador>
        </TomadorServico>
      </Nfse>
    </CompNfse>
    """


@pytest.fixture
def xml_cte_minimo():
    # CT-e em cteProc (estrutura mínima)
    return """<?xml version="1.0" encoding="UTF-8"?>
    <cteProc xmlns="http://www.portalfiscal.inf.br/cte">
      <CTe>
        <infCte Id="CTe50123456789012345678901234567890123456789012">
          <ide>
            <dhEmi>2025-09-04T12:34:56</dhEmi>
          </ide>
          <emit>
            <CNPJ>11111111000111</CNPJ>
          </emit>
          <dest>
            <CNPJ>22222222000122</CNPJ>
          </dest>
        </infCte>
      </CTe>
      <protCTe>
        <infProt>
          <nProt>CTE-PROT-0001</nProt>
        </infProt>
      </protCTe>
    </cteProc>
    """


@pytest.fixture
def xml_mdfe_minimo():
    # MDF-e em mdfeProc (estrutura mínima)
    return """<?xml version="1.0" encoding="UTF-8"?>
    <mdfeProc xmlns="http://www.portalfiscal.inf.br/mdfe">
      <MDFe>
        <infMDFe Id="MDFe35123456789012345678901234567890123456789012">
          <ide>
            <dhEmi>2025-09-04T08:00:00</dhEmi>
          </ide>
          <emit>
            <CNPJ>33333333000133</CNPJ>
          </emit>
        </infMDFe>
      </MDFe>
      <protMDFe>
        <infProt>
          <nProt>MDFE-PROT-0001</nProt>
        </infProt>
      </protMDFe>
    </mdfeProc>
    """


# =========================
# Testes
# =========================

def test_nfe_basico(dfe, xml_nfe_minimo):
    out = dfe.parse_string(xml_nfe_minimo)
    assert out["tipo_documento"] == "NF-e"
    assert out["chave_acesso"].startswith("35100123")
    assert out["cnpj_emitente"] == "12345678000195"
    assert out["cnpj_destinatario"] == "98765432000188"
    assert out["protocolo"] == "1234567890"
    assert out["data_emissao"].startswith("2025-09-04")
    # aliases compat (se expostos)
    if "cnpj" in out:
        assert out["cnpj"] == "12345678000195"
    if "destinatario" in out:
        assert out["destinatario"] in ("98765432000188", "12345678000195")


def test_evento_basico(dfe, xml_evento_minimo):
    out = dfe.parse_string(xml_evento_minimo)
    assert out["tipo_documento"] == "Evento"
    assert out.get("isevent") == "1"
    assert out["chave_acesso"].startswith("35100123")
    assert out["tipo_evento"] in ("110111", "Cancelamento")
    assert out["sequencia_evento"] == "1"
    assert out["cnpj_emitente"] == "12345678000195"
    assert out["data_evento"].startswith("2025-09-04")


def test_nfse_basico(dfe, xml_nfse_minimo):
    out = dfe.parse_string(xml_nfse_minimo)
    assert out["tipo_documento"] == "NFS-e"
    assert out["chave_acesso"] == "20250001"
    assert out["cnpj_emitente"] == "12345678000195"
    assert out["cnpj_destinatario"] == "98765432000188"
    assert out["data_emissao"].startswith("2025-09-04")


def test_cte_basico(dfe, xml_cte_minimo):
    out = dfe.parse_string(xml_cte_minimo)
    assert out["tipo_documento"] == "CT-e", f"tipo_documento inesperado: {out}"
    assert out["chave_acesso"].startswith("50123456"), f"chave_acesso inválida: {out.get('chave_acesso')}"
    assert out["cnpj_emitente"] == "11111111000111", f"emitente errado: {out.get('cnpj_emitente')}"
    assert out["cnpj_destinatario"] == "22222222000122", f"dest errado: {out.get('cnpj_destinatario')}"
    assert out["protocolo"] == "CTE-PROT-0001", f"protocolo ausente/errado: {out.get('protocolo')}"
    assert out["data_emissao"].startswith("2025-09-04"), f"data_emissao não normalizada: {out.get('data_emissao')}"

def test_mdfe_basico(dfe, xml_mdfe_minimo):
    out = dfe.parse_string(xml_mdfe_minimo)
    assert out["tipo_documento"] == "MDF-e", f"tipo_documento inesperado: {out}"
    assert out["chave_acesso"].startswith("35123456"), f"chave_acesso inválida: {out.get('chave_acesso')}"
    assert out["cnpj_emitente"] == "33333333000133", f"emitente errado: {out.get('cnpj_emitente')}"
    assert out["protocolo"] == "MDFE-PROT-0001", f"protocolo ausente/errado: {out.get('protocolo')}"
    assert out["data_emissao"].startswith("2025-09-04"), f"data_emissao não normalizada: {out.get('data_emissao')}"



# =========================
# Main para rodar com F5
# =========================
if __name__ == "__main__":
    import sys
    # -v   : verbose (mostra nome/status de cada teste)
    # -rA  : resumo de todos os resultados (passed/failed/xfail/skip)
    # -s   : mostra prints (se colocar prints nos testes)
    sys.exit(pytest.main([__file__, "-v", "-rA", "-s"]))
# =========================