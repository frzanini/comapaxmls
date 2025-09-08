from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

class FieldType(str, Enum):
    A = "A"  # Alfanumérico (com aspas)
    N = "N"  # Numérico (ponto decimal)
    I = "I"  # Inteiro (sem aspas)
    L = "L"  # Lógico ("S"/"N")

@dataclass
class LayoutField:
    name: str
    ftype: FieldType
    decimals: Optional[int] = None
    default: Any = None

@dataclass
class Layout:
    name: str
    fields: List[LayoutField]

class Formatter:
    @staticmethod
    def _to_decimal(v: Any, places: int) -> str:
        d = Decimal(str(v or 0))
        q = Decimal(10) ** -places
        return str(d.quantize(q, rounding=ROUND_HALF_UP))

    @classmethod
    def fmt(cls, f: LayoutField, value: Any) -> str:
        t = f.ftype
        if t == FieldType.A:
            sval = "" if value is None else str(value)
            return f'"{sval}"'
        if t == FieldType.I:
            return str(int(value or 0))
        if t == FieldType.N:
            places = f.decimals if f.decimals is not None else 2
            return cls._to_decimal(value, places)
        if t == FieldType.L:
            sval = str(value or "N").strip().lower()
            # padroniza para "S"/"N"
            return "S" if sval in {"s", "sim", "true", "1", "y", "yes"} else "N"
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
