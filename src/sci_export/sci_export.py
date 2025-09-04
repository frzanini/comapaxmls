# src/sci_export/sci_export.py
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

# --- Importa o adapter novo (no mesmo repo) ---
from dfe.DocumentoFiscalParser import DocumentoFiscalSCIAdapter, NFeSCI, NFeItemSCI  # type: ignore

log = logging.getLogger(__name__)
if not log.handlers:
    h = logging.StreamHandler()
    fmt = logging.Formatter("[%(levelname)s] %(message)s")
    h.setFormatter(fmt)
    log.addHandler(h)
    log.setLevel(logging.INFO)

# --------------------- Formatadores básicos (SCI) ----------------------------
_DEC = Decimal

def fmt_num(v: Optional[Decimal], casas: str = "0.00") -> str:
    if v is None:
        return ""
    try:
        q = _DEC(v).quantize(_DEC(casas), rounding=ROUND_HALF_UP)
        return f"{q}"
    except Exception:
        return ""

def fmt_text(s: Optional[str]) -> str:
    return (s or "").strip()

# --------------------- Mapeadores de Anexos ----------------------------------
def map_anexo04(n: NFeSCI) -> List[str]:
    """
    Anexo 04 – Registro de Saídas (por NF)
    Exemplo mínimo (ajuste aos seus nomes/ordem de colunas):
    """
    h = n.header
    return [
        fmt_text(h.chave_acesso),
        fmt_text(h.cnpj_emitente),
        fmt_text(h.cnpj_destinatario),
        fmt_text(h.data_emissao_ymd),
        fmt_text(h.modelo),
        fmt_text(h.serie),
        fmt_text(h.numero),
        fmt_text(h.protocolo),
    ]

def map_anexo09(n: NFeSCI) -> List[str]:
    """
    Anexo 09 – Registro de Entradas (por NF)
    """
    h = n.header
    return [
        fmt_text(h.chave_acesso),
        fmt_text(h.cnpj_emitente),
        fmt_text(h.cnpj_destinatario),
        fmt_text(h.data_entrada_ymd or h.data_emissao_ymd),
        fmt_text(h.modelo),
        fmt_text(h.serie),
        fmt_text(h.numero),
        fmt_text(h.protocolo),
    ]

def map_anexo07(n: NFeSCI, it: NFeItemSCI) -> List[str]:
    """
    Anexo 07 – Produtos (por item da NF)
    """
    h = n.header
    return [
        fmt_text(h.chave_acesso),
        fmt_text(it.cProd),
        fmt_text(it.xProd),
        fmt_text(it.NCM),
        fmt_text(it.CFOP),
        fmt_text(it.uCom),
        fmt_num(it.qCom, "0.0000"),
        fmt_num(it.vUnCom, "0.0000"),
        fmt_num(it.vProd, "0.00"),
        fmt_text(it.CEST),
        fmt_text(it.CST),
        fmt_text(it.EAN),
    ]

# --------------------- Iteração e filtros ------------------------------------
def iter_nfe(adapter: DocumentoFiscalSCIAdapter, base: Path) -> Iterable[NFeSCI]:
    for p in sorted(base.rglob("*.xml")):
        try:
            xml_text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        nfe = adapter.parse_nfe_with_items(xml_text)
        if nfe:
            yield nfe

def matches_filters(adapter: DocumentoFiscalSCIAdapter, n: NFeSCI,
                    cnpj: Optional[str], ano: Optional[int], mes: Optional[int], dia: Optional[int],
                    anexo: str) -> bool:
    # data
    if not adapter.nota_matches_date(n, ano, mes, dia):
        return False

    # cnpj/direção
    if cnpj:
        dir_ = adapter.direction(n, cnpj)
        if anexo == "04" and dir_ != "saida":
            return False
        if anexo == "09" and dir_ != "entrada":
            return False
        # Anexo 07: segue a direção da própria NF conforme o filtro aplicado via anexo escolhido
        if anexo == "07" and dir_ not in {"entrada", "saida"}:
            return False

    return True

# --------------------- Writer -------------------------------------------------
def write_rows(path: Path, header_cols: List[str], rows: List[List[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        if header_cols:
            f.write(";".join(header_cols) + "\n")
        for r in rows:
            f.write(";".join("" if v is None else str(v) for v in r) + "\n")

# --------------------- CLI / Main --------------------------------------------
def run_cli() -> None:
    ap = argparse.ArgumentParser("SCI Export")
    ap.add_argument("--input", "-i", type=str, required=True, help="Pasta base com XMLs")
    ap.add_argument("--output", "-o", type=str, required=True, help="Pasta de saída")
    ap.add_argument("--anexo", "-a", type=str, required=True, choices=("04", "07", "09"))
    ap.add_argument("--cnpj", type=str, default=None, help="CNPJ alvo (gera Saída para 04 e Entrada para 09)")
    ap.add_argument("--ano", type=int, default=None)
    ap.add_argument("--mes", type=int, default=None)
    ap.add_argument("--dia", type=int, default=None)
    ap.add_argument("--por-cnpj", action="store_true", help="Particionar saída por CNPJ/AAAA/MM(/DD)")
    args = ap.parse_args()

    base = Path(args.input)
    out_base = Path(args.output)
    adapter = DocumentoFiscalSCIAdapter()

    rows: List[List[str]] = []
    header: List[str] = []
    # Seleciona mapeador conforme anexo
    if args.anexo == "04":
        header = ["chave", "cnpj_emit", "cnpj_dest", "data_emi_yyyymmdd", "modelo", "serie", "numero", "protocolo"]
        mapper = map_anexo04
    elif args.anexo == "09":
        header = ["chave", "cnpj_emit", "cnpj_dest", "data_ent_yyyymmdd", "modelo", "serie", "numero", "protocolo"]
        mapper = map_anexo09
    else:
        header = ["chave", "cProd", "xProd", "NCM", "CFOP", "uCom", "qCom", "vUnCom", "vProd", "CEST", "CST", "EAN"]
        # mapper de item exige 2 parâmetros → trataremos abaixo

    if not args.por_cnpj:
        # Saída única
        if args.anexo in {"04", "09"}:
            for n in iter_nfe(adapter, base):
                if not matches_filters(adapter, n, args.cnpj, args.ano, args.mes, args.dia, args.anexo):
                    continue
                rows.append(mapper(n))
            out = out_base / f"anexo_{args.anexo}.txt"
            write_rows(out, header, rows)
            log.info("Gerado: %s (%d linhas)", out, len(rows))
        else:
            # Anexo 07: por item
            for n in iter_nfe(adapter, base):
                if not matches_filters(adapter, n, args.cnpj, args.ano, args.mes, args.dia, args.anexo):
                    continue
                for it in n.itens:
                    rows.append(map_anexo07(n, it))
            out = out_base / "anexo_07.txt"
            write_rows(out, header, rows)
            log.info("Gerado: %s (%d linhas)", out, len(rows))
        return

    # --- Particionado por CNPJ/AAAA/MM(/DD)
    def out_path(cnpj: Optional[str], ymd: Optional[str]) -> Path:
        if not args.por_cnpj:
            return out_base / f"anexo_{args.anexo}.txt"
        # quebra em /CNPJ/AAAA/MM(/DD)/arquivo.txt
        cnpj_dir = (cnpj or "desconhecido").zfill(14)[:14]
        if ymd and len(ymd) == 8:
            yyyy, mm, dd = ymd[:4], ymd[4:6], ymd[6:8]
            sub = out_base / cnpj_dir / yyyy / mm / (dd if args.dia else "")
        else:
            sub = out_base / cnpj_dir
        sub = Path(str(sub))  # normaliza caso dd seja ""
        return sub / f"anexo_{args.anexo}.txt"

    # Em modo particionado, escreve múltiplos arquivos
    buckets: dict[Path, List[List[str]]] = {}
    if args.anexo in {"04", "09"}:
        for n in iter_nfe(adapter, base):
            if not matches_filters(adapter, n, args.cnpj, args.ano, args.mes, args.dia, args.anexo):
                continue
            h = n.header
            ref_cnpj = (h.cnpj_emitente if args.anexo == "04" else h.cnpj_destinatario)
            ref_ymd  = (h.data_emissao_ymd if args.anexo == "04" else (h.data_entrada_ymd or h.data_emissao_ymd))
            p = out_path(ref_cnpj, ref_ymd)
            buckets.setdefault(p, []).append(map_anexo04(n) if args.anexo == "04" else map_anexo09(n))
    else:
        for n in iter_nfe(adapter, base):
            if not matches_filters(adapter, n, args.cnpj, args.ano, args.mes, args.dia, args.anexo):
                continue
            h = n.header
            # para itens, use CNPJ conforme direção detectada (ou emitente se não houver filtro)
            ref_cnpj = h.cnpj_emitente
            if args.cnpj:
                dir_ = adapter.direction(n, args.cnpj)
                ref_cnpj = h.cnpj_emitente if dir_ == "saida" else h.cnpj_destinatario
            ref_ymd = h.data_emissao_ymd
            p = out_path(ref_cnpj, ref_ymd)
            for it in n.itens:
                buckets.setdefault(p, []).append(map_anexo07(n, it))

    for p, lines in buckets.items():
        write_rows(p, header, lines)
        log.info("Gerado: %s (%d linhas)", p, len(lines))

if __name__ == "__main__":
    run_cli()
