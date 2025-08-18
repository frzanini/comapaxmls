from __future__ import annotations
import argparse
from datetime import datetime
from .config import SiegConfig
from .types import XmlType
from .service import SiegIngestionService

def _parse_types(lst): 
    out=[]; 
    for s in lst:
        try: out.append(XmlType[s.upper()])
        except KeyError: pass
    return tuple(out) or (XmlType.NFE,)

def main():
    ap = argparse.ArgumentParser("SIEG -> S3")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("intervalo_dias")
    s1.add_argument("--days-back", type=int, default=1)
    s1.add_argument("--xml-types", nargs="*", default=["NFE"])
    s1.add_argument("--include-events", action="store_true")
    s1.add_argument("--cnpj-cpf", default=None)
    s1.add_argument("--participante", choices=["emitente","destinatario","ambos"], default="ambos")
    s1.add_argument("--incluir-dest-quando-emitente", action="store_true")

    s2 = sub.add_parser("ano_mes")
    s2.add_argument("--year", type=int, required=True)
    s2.add_argument("--month", type=int, required=True)
    s2.add_argument("--xml-types", nargs="*", default=["NFE"])
    s2.add_argument("--include-events", action="store_true")
    s2.add_argument("--cnpj-cpf", default=None)
    s2.add_argument("--participante", choices=["emitente","destinatario","ambos"], default="ambos")
    s2.add_argument("--incluir-dest-quando-emitente", action="store_true")

    s3 = sub.add_parser("emissao")
    s3.add_argument("--start", required=True)
    s3.add_argument("--end", required=True)
    s3.add_argument("--xml-types", nargs="*", default=["NFE"])
    s3.add_argument("--include-events", action="store_true")
    s3.add_argument("--cnpj-cpf", default=None)
    s3.add_argument("--participante", choices=["emitente","destinatario","ambos"], default="ambos")
    s3.add_argument("--incluir-dest-quando-emitente", action="store_true")

    args = ap.parse_args()
    svc = SiegIngestionService(SiegConfig.from_env())

    if args.cmd == "intervalo_dias":
        svc.baixar_intervalo_dias(days_back=args.days_back, xml_types=_parse_types(args.xml_types),
            include_events=args.include_events, cnpj=args.cnpj_cpf,
            participante=args.participante, incluir_dest_quando_emitente=args.incluir_dest_quando_emitente)
    elif args.cmd == "ano_mes":
        if args.cnpj_cpf:
            svc.baixar_por_cnpj_ano_mes(cnpj=args.cnpj_cpf, year=args.year, month=args.month,
                incluir_eventos=args.include_events, xml_types=_parse_types(args.xml_types),
                participante=args.participante, incluir_dest_quando_emitente=args.incluir_dest_quando_emitente)
        else:
            ini, fim = svc.month_range(args.year, args.month)
            svc.download_por_participante(start_date=ini, end_date=fim, xml_types=_parse_types(args.xml_types),
                include_events=args.include_events, cnpj=None, participante="ambos",
                incluir_dest_quando_emitente=False)
    elif args.cmd == "emissao":
        start = datetime.fromisoformat(args.start.replace("Z","+00:00"))
        end   = datetime.fromisoformat(args.end.replace("Z","+00:00"))
        svc.download_por_participante(start_date=start, end_date=end, xml_types=_parse_types(args.xml_types),
            include_events=args.include_events, cnpj=args.cnpj_cpf, participante=args.participante,
            incluir_dest_quando_emitente=args.incluir_dest_quando_emitente)

if __name__ == "__main__":
    main()
