"""Limpieza / filtrado del archivo Reporteador.

Reglas:
- Se conservan solo las columnas: NUMERO, ORD_COMPRA, PRODUCTO, REGISTRO, RUC.
- NUMERO: sin cambios.
- ORD_COMPRA:
    * Si ya tiene un número -> no se modifica.
    * Si está vacío, se mira el inicio de PRODUCTO:
        - Caso A: número simple ("31015 ...")     -> se antepone "100" -> "10031015".
        - Caso B: número con guiones ("31116-1 ..") -> se deja igual  -> "31116-1".
        - Caso C: no hay número al inicio           -> queda vacío.
- PRODUCTO: se le quita el número inicial (el de ORD_COMPRA) y queda limpio.
- REGISTRO y RUC: sin cambios.
- Se eliminan filas duplicadas exactas.
"""

import re
from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.services.excel_utils import ProcesamientoError, read_table, write_xlsx

REQUIRED_COLUMNS = ["NUMERO", "ORD_COMPRA", "PRODUCTO", "REGISTRO", "RUC"]
OUTPUT_COLUMNS = ["NUMERO", "ORD_COMPRA", "PRODUCTO", "REGISTRO", "RUC", "DETRACCION"]
AVANCE_FILENAME = "reporteador_avance.xlsx"

# La columna DETRACCION (salida) puede venir con distintos nombres en el origen.
_DETRACCION_ALIASES = [
    "DETRACCION",
    "DETRACCIÓN",
    "DETRA_TASA",
    "DETRA TASA",
    "DETRA-TASA",
]

# Número al inicio: dígitos, opcionalmente seguido de segmentos "-dígitos",
# y (opcionalmente) el resto del texto del producto.
_LEADING_NUM_RE = re.compile(r"^\s*(\d+(?:-\d+)*)(?:\s+(.*\S))?\s*$")


def avance_path() -> Path:
    return Path(settings.REPORTS_DIR) / AVANCE_FILENAME


def _is_empty(value) -> bool:
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.lower() == "nan"


def _clean_id(value) -> str:
    """Normaliza un identificador de texto (quita un '.0' sobrante de floats)."""
    if _is_empty(value):
        return ""
    s = str(value).strip()
    if re.fullmatch(r"\d+\.0", s):
        s = s[:-2]
    return s


def _clean_ord_and_producto(ord_raw, producto_raw) -> tuple[str, str]:
    producto = "" if _is_empty(producto_raw) else str(producto_raw).strip()

    match = _LEADING_NUM_RE.match(producto)
    if match:
        leading = match.group(1)
        rest = (match.group(2) or "").strip()
    else:
        leading = None
        rest = producto

    if not _is_empty(ord_raw):
        # Ya tiene número -> no se modifica.
        ord_final = _clean_id(ord_raw)
    elif leading is None:
        # Caso C: sin número al inicio.
        ord_final = ""
    elif "-" in leading:
        # Caso B: número con guiones -> se deja igual.
        ord_final = leading
    else:
        # Caso A: número simple -> se antepone "100".
        ord_final = "100" + leading

    return ord_final, rest


def _resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """Mapea nombre normalizado (MAYÚSCULAS) -> nombre real de columna."""
    mapping = {str(col).strip().upper(): col for col in df.columns}
    missing = [c for c in REQUIRED_COLUMNS if c not in mapping]
    if missing:
        raise ProcesamientoError(
            "El archivo no contiene las columnas requeridas: " + ", ".join(missing)
        )
    return mapping


def process_reporteador(filename: str, content: bytes) -> dict:
    """Procesa el Reporteador y guarda el avance en disco. Devuelve un resumen."""
    df = read_table(filename, content)
    cols = _resolve_columns(df)
    # DETRACCION viene del propio Reporteador (columna opcional, varios alias).
    detraccion_col = next(
        (cols[a] for a in _DETRACCION_ALIASES if a in cols), None
    )

    rows: list[list[str]] = []
    for _, row in df.iterrows():
        numero = _clean_id(row[cols["NUMERO"]])
        ord_final, producto = _clean_ord_and_producto(
            row[cols["ORD_COMPRA"]], row[cols["PRODUCTO"]]
        )
        registro = _clean_id(row[cols["REGISTRO"]])
        ruc = _clean_id(row[cols["RUC"]])

        # Saltar filas totalmente vacías.
        if all(
            _is_empty(v) for v in (numero, ord_final, producto, registro, ruc)
        ):
            continue

        detraccion = (
            _clean_id(row[detraccion_col]) if detraccion_col is not None else ""
        )
        # DETRACCION vacía -> 0.
        if _is_empty(detraccion):
            detraccion = "0"
        rows.append([numero, ord_final, producto, registro, ruc, detraccion])

    out_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

    # Eliminar filas duplicadas exactas (mismas 5 columnas), conservando la primera.
    total_rows = len(out_df)
    out_df = out_df.drop_duplicates(keep="first").reset_index(drop=True)
    duplicates_removed = total_rows - len(out_df)

    output_path = avance_path()
    write_xlsx(out_df, output_path, sheet_name="Reporteador")

    return {
        "rows": int(len(out_df)),
        "duplicates_removed": int(duplicates_removed),
        "file": str(output_path),
    }
