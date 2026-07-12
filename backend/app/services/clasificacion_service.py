"""Clasificación del merge en categorías (operaciones).

Reglas (por ahora):
- RUC nacional = 11 dígitos que empiezan con 10 o 20. Todo lo demás es EXTERIOR.
- EXTERIOR                 -> Operación 6.
- NACIONAL + SOL           -> Operación 1.
- NACIONAL + USD           -> Operación 2.
"""

import re
from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.models.operacion import Operacion
from app.services.excel_utils import write_xlsx

SIN_CATEGORIA = "Sin categoría"
CLASIFICADO_FILENAME = "informe_clasificado.xlsx"

# Posibles nombres de la columna de fecha de vencimiento.
_FEC_VCTO_ALIASES = [
    "FEC. VCTO",
    "FEC.VCTO",
    "FEC VCTO",
    "F. VCTO",
    "F VCTO",
    "FECHA VCTO",
    "FECHA DE VENCIMIENTO",
    "FECHA VENCIMIENTO",
]


def clasificado_path() -> Path:
    return Path(settings.REPORTS_DIR) / CLASIFICADO_FILENAME


def es_ruc_nacional(ruc) -> bool:
    r = re.sub(r"\.0$", "", str(ruc).strip())
    return len(r) == 11 and r.isdigit() and r[:2] in ("10", "20")


def _posicion_objetivo(ruc, moneda) -> int | None:
    """Posición (1-based) de la operación destino según las reglas."""
    if es_ruc_nacional(ruc):
        m = str(moneda).strip().upper()
        if m == "SOL":
            return 1
        if m == "USD":
            return 2
        return None
    return 6  # exterior


def _etiqueta(pos: int, op: Operacion) -> str:
    return f"Operación {pos} - {op.texto}" if op.texto else f"Operación {pos}"


_DATETIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}:\d{2}(\.\d+)?$")


def _strip_hora(value):
    """Quita la hora de valores datetime ('2025-06-15 00:00:00' -> '2025-06-15')."""
    if isinstance(value, str):
        m = _DATETIME_RE.match(value)
        if m:
            return m.group(1)
    return value


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", str(name)).strip().upper()


def _resolve_col(df: pd.DataFrame, name: str) -> str | None:
    for col in df.columns:
        if str(col).strip().upper() == name:
            return col
    return None


def _resolve_fecha_col(df: pd.DataFrame) -> str | None:
    aliases = {_norm(a) for a in _FEC_VCTO_ALIASES}
    for col in df.columns:
        if _norm(col) in aliases:
            return col
    return None


def clasificar_dataframe(
    df: pd.DataFrame, operaciones: list[Operacion]
) -> pd.DataFrame:
    by_pos = {i + 1: op for i, op in enumerate(operaciones)}
    ruc_col = _resolve_col(df, "RUC")
    moneda_col = _resolve_col(df, "MONEDA")

    etiquetas: list[str] = []
    for _, row in df.iterrows():
        ruc = row[ruc_col] if ruc_col else ""
        moneda = row[moneda_col] if moneda_col else ""
        pos = _posicion_objetivo(ruc, moneda)
        op = by_pos.get(pos) if pos else None
        etiquetas.append(_etiqueta(pos, op) if op else SIN_CATEGORIA)

    out = df.copy()
    out.insert(0, "OPERACION", etiquetas)
    return out


def _fechas_iso(df: pd.DataFrame, fecha_col: str) -> list[str]:
    """Convierte la columna de fecha a ISO (YYYY-MM-DD); vacío si no parsea."""
    parsed = pd.to_datetime(
        df[fecha_col], errors="coerce", dayfirst=True, format="mixed"
    )
    iso = parsed.dt.strftime("%Y-%m-%d").where(parsed.notna(), "")
    return iso.tolist()


def clasificar_merge(path: Path, operaciones: list[Operacion]) -> dict:
    """Devuelve el merge clasificado como estructura JSON-serializable.

    Cada fila trae `__pos` = posición (1-based) de la operación asignada, y se
    incluye la lista de operaciones para que el frontend arme el desplegable.
    """
    df = pd.read_excel(path, dtype=str).fillna("")
    df = df.map(_strip_hora)
    columnas = list(df.columns)

    ruc_col = _resolve_col(df, "RUC")
    moneda_col = _resolve_col(df, "MONEDA")
    fecha_col = _resolve_fecha_col(df)
    iso_list = _fechas_iso(df, fecha_col) if fecha_col else None
    n = len(operaciones)

    filas = df.to_dict(orient="records")
    for idx, rec in enumerate(filas):
        ruc = rec.get(ruc_col, "") if ruc_col else ""
        moneda = rec.get(moneda_col, "") if moneda_col else ""
        pos = _posicion_objetivo(ruc, moneda)
        rec["__pos"] = pos if (pos and pos <= n) else None
        if iso_list is not None:
            rec["__fec_vcto"] = iso_list[idx]

    operaciones_out = [
        {
            "pos": i + 1,
            "texto": op.texto,
            "moneda": op.moneda,
            "ambito": op.ambito,
        }
        for i, op in enumerate(operaciones)
    ]

    return {
        "columnas": columnas,
        "filas": filas,
        "operaciones": operaciones_out,
        "fecha_columna": fecha_col,
    }


def escribir_clasificado(path: Path, operaciones: list[Operacion]) -> Path:
    df = pd.read_excel(path, dtype=str).fillna("")
    df = clasificar_dataframe(df, operaciones)
    output_path = clasificado_path()
    write_xlsx(df, output_path, sheet_name="Informe")
    return output_path
