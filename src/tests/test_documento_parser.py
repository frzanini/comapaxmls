import pytest
from dfe.DocumentoFiscalParser import DocumentoFiscalParser

@pytest.fixture
def parser():
    return DocumentoFiscalParser()

# XML mínimo de NF-e (mock simplificado)
@pytest.fixture
def xml_nfe_minimo():
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

def test_parse_nfe_minimo(parser, xml_nfe_minimo):
    out = parser.parse_documento_fiscal_string(xml_nfe_minimo)
    assert out["tipo_documento"] == "NF-e"
    assert out["chave_acesso"].startswith("35100123")
    assert out["cnpj_emitente"] == "12345678000195"
    assert out["cnpj_destinatario"] == "98765432000188"
    assert out["protocolo"] == "1234567890"
    assert out["data_emissao"].startswith("2025-09-04")

# XML mínimo de Evento (mock simplificado)
@pytest.fixture
def xml_evento_minimo():
    return """<?xml version="1.0" encoding="UTF-8"?>
    <procEventoNFe xmlns="http://www.portalfiscal.inf.br/nfe">
      <evento>
        <infEvento>
          <chNFe>35100123000000000000550010000000011000000012</chNFe>
          <tpEvento>110111</tpEvento>
          <nSeqEvento>1</nSeqEvento>
          <CNPJ>12345678000195</CNPJ>
          <dhEvento>2025-09-04T15:00:00</dhEvento>
        </infEvento>
      </evento>
    </procEventoNFe>
    """

def test_parse_evento_minimo(parser, xml_evento_minimo):
    out = parser.parse_documento_fiscal_string(xml_evento_minimo)
    assert out["tipo_documento"] == "Evento"
    assert out["isevent"] == "1"
    assert out["chave_acesso"].startswith("35100123")
    assert out["tipo_evento"] == "110111"
    assert out["sequencia_evento"] == "1"
    assert out["cnpj_emitente"] == "12345678000195"
    assert out["data_evento"].startswith("2025-09-04")

# XML mínimo de NFS-e (mock simplificado)
@pytest.fixture
def xml_nfse_minimo():
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

def test_parse_nfse_minimo(parser, xml_nfse_minimo):
    out = parser.parse_documento_fiscal_string(xml_nfse_minimo)
    assert out["tipo_documento"] == "NFS-e"
    assert out["chave_acesso"] == "20250001"
    assert out["cnpj_emitente"] == "12345678000195"
    assert out["cnpj_destinatario"] == "98765432000188"
    assert out["data_emissao"].startswith("2025-09-04")

# --- Main para rodar direto com F5 ---
if __name__ == "__main__":
    import sys, pytest
    # -v : verbose (mostra nome de cada teste e status)
    # -rA : mostra resumo de TODOS (passed, failed, skipped)
    sys.exit(pytest.main([__file__, "-s", "-v", "-rA"]))

