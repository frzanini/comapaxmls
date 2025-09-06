from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

class FieldType(str, Enum):
    A = "A"  # Alfanumérico (com aspas)
    N = "N"  # Numérico (ponto decimal)
    I = "I"  # Inteiro (sem aspas)
    L = "L"  # Lógico ("Sim"/"Não")

@dataclass
class LayoutField:
    name: str
    ftype: FieldType
    decimals: Optional[int] = None
    default: Any = ""

@dataclass
class Layout:
    name: str
    fields: List[LayoutField]

class Formatter:
    @staticmethod
    def _num(value: Any, decimals: int) -> str:
        try:
            d = Decimal(str(value))
        except Exception:
            d = Decimal("0")
        q = Decimal("1").scaleb(-decimals)
        d = d.quantize(q, rounding=ROUND_HALF_UP)
        return f"{d:.{decimals}f}" if decimals > 0 else f"{d}"

    @staticmethod
    def fmt(field: LayoutField, value: Any) -> str:
        t = field.ftype
        if t == FieldType.A:
            safe_val = "" if value is None else str(value)
            return f"\"{safe_val}\""
        if t == FieldType.I:
            try:
                return str(int(Decimal(str(value or 0))))
            except Exception:
                return "0"
        if t == FieldType.N:
            return Formatter._num(value or field.default or 0, field.decimals or 0)
        if t == FieldType.L:
            if isinstance(value, bool):
                return "Sim" if value else "Não"
            sval = str(value).strip().lower()
            return "Sim" if sval in {"s", "sim", "true", "1"} else "Não"
        raise ValueError(f"Tipo de campo desconhecido: {t}")

    @classmethod
    def emit_row(cls, layout: Layout, row: Dict[str, Any]) -> str:
        return ",".join(cls.fmt(f, row.get(f.name, f.default)) for f in layout.fields)

    @staticmethod
    def write_rows(path, layout: Layout, rows: Iterable[Dict[str, Any]]) -> int:
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for row in rows:
                f.write(Formatter.emit_row(layout, row) + "\n")
                count += 1
        return count
