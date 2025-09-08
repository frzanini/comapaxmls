from __future__ import annotations
import argparse
from datetime import datetime
from settings import Settings
from db_repository import Paper
from exporter import SciExporter


def _parse_date(s: str):
    return datetime.strptime(s, "%Y-%m-%d").date()


"""
Ponto de entrada principal para a ferramenta de linha de comando de exportação SCI TXT.
Esta função configura os parâmetros necessários para exportar dados SCI, incluindo CNPJ, intervalo de datas, tipo de papel e anexos a serem gerados.
Inicializa as configurações da aplicação e o exportador, então executa o processo de exportação usando os parâmetros fornecidos.
O processo de exportação envolve gerar arquivos TXT a partir do banco de dados, opcionalmente enviar para o S3, realizar o parsing e finalizar a exportação.
Todos os recursos são devidamente fechados após a execução.
Args:
    argv (list[str], opcional): Argumentos de linha de comando. Se None, utiliza parâmetros padrão para teste.
Exceções:
    Quaisquer exceções levantadas durante o processo de exportação são propagadas após a limpeza dos recursos.
"""
def main(argv=None):
    # ap = argparse.ArgumentParser(description="SCI TXT Export — DB→S3→Parser→TXT")
    # ap.add_argument("--cnpj", required=True, help="CNPJ alvo (emitente/destinatário)")
    # ap.add_argument("--inicio", required=True, help="Data início (YYYY-MM-DD)")
    # ap.add_argument("--fim", required=True, help="Data fim (YYYY-MM-DD)")
    # ap.add_argument("--papel", choices=[Paper.EMITENTE, Paper.DESTINATARIO, Paper.AMBOS], default=Paper.AMBOS)
    # ap.add_argument("--anexo", action="append", choices=["04", "07", "09"], help="Anexos a gerar. Padrão: 04,07,09")
    # args = ap.parse_args(argv)

    cnpj = "08959064000126" #"08959064000126" #34228897000127
    inicio = "2025-09-01"
    fim = "2025-09-07"
    papel = "ambos"
    #anexo 04 --anexo 07 --anexo 09

    st = Settings()
    #anexos = set(args.anexo or ["04", "07", "09"])  # todos por padrão
    anexos = set(["04", "07", "09"])  # todos por padrão
    #anexos = set(["04","09"]) 

    exp = SciExporter(st)
    try:
        # exp.generate(
        #     cnpj=args.cnpj,
        #     inicio=_parse_date(args.inicio),
        #     fim=_parse_date(args.fim),
        #     papel=args.papel,
        #     anexos=sorted(anexos),
        # )

        exp.generate(
            cnpj=cnpj,
            inicio=_parse_date(inicio),
            fim=_parse_date(fim),
            papel=papel,
            anexos=sorted(anexos),
        )

    finally:
        exp.close()


if __name__ == "__main__":
    main()