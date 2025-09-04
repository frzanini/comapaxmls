from dfe.DocumentoFiscalParser import DocumentoFiscalSCIAdapter

EX_XML = """<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe><infNFe Id="NFe123">
    <ide><mod>55</mod><serie>1</serie><nNF>100</nNF><dhEmi>2025-08-10T12:34:56-03:00</dhEmi></ide>
    <emit><CNPJ>11111111000191</CNPJ></emit>
    <dest><CNPJ>22222222000155</CNPJ></dest>
    <det nItem="1"><prod><cProd>P1</cProd><xProd>X</xProd><NCM>1234</NCM><CFOP>5102</CFOP><uCom>UN</uCom><qCom>2</qCom><vUnCom>10</vUnCom><vProd>20</vProd></prod></det>
  </infNFe></NFe></nfeProc>"""

def test_parse_nfe_with_items_basic():
    a = DocumentoFiscalSCIAdapter()
    n = a.parse_nfe_with_items(EX_XML)
    assert n is not None
    assert n.header.cnpj_emitente == "11111111000191"
    assert n.header.cnpj_destinatario == "22222222000155"
    assert n.header.data_emissao_ymd == "20250810"
    assert len(n.itens) == 1
    assert n.itens[0].cProd == "P1"


if __name__ == "__main__":
    test_parse_nfe_with_items_basic()
    print("OK")