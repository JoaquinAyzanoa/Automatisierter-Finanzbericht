"""Combinación de DOLARES y SOLES PROVEEDORES en un solo archivo.

- A DOLARES PROVEEDORES se le agrega la columna MONEDA = "USD".
- A SOLES PROVEEDORES se le agrega la columna MONEDA = "SOL".
- Ambos archivos (mismas columnas) se combinan en uno solo.
"""

from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.services.excel_utils import read_table, write_xlsx

AVANCE_FILENAME = "proveedores_avance.xlsx"
MONEDA_COLUMN = "MONEDA"


def avance_path() -> Path:
    return Path(settings.REPORTS_DIR) / AVANCE_FILENAME


def _with_moneda(df: pd.DataFrame, valor: str) -> pd.DataFrame:
    """Agrega (o reemplaza) la columna MONEDA como primera columna."""
    existing = [c for c in df.columns if str(c).strip().upper() == MONEDA_COLUMN]
    if existing:
        df = df.drop(columns=existing)
    df = df.copy()
    df.insert(0, MONEDA_COLUMN, valor)
    return df


def process_proveedores(
    dolares_filename: str,
    dolares_content: bytes,
    soles_filename: str,
    soles_content: bytes,
) -> dict:
    """Combina ambos archivos en uno y guarda el avance. Devuelve un resumen."""
    df_usd = read_table(dolares_filename, dolares_content).dropna(how="all")
    df_sol = read_table(soles_filename, soles_content).dropna(how="all")

    df_usd = _with_moneda(df_usd, "USD")
    df_sol = _with_moneda(df_sol, "SOL")

    combined = pd.concat([df_usd, df_sol], ignore_index=True)

    output_path = avance_path()
    write_xlsx(combined, output_path, sheet_name="Proveedores")

    return {
        "rows": int(len(combined)),
        "dolares_rows": int(len(df_usd)),
        "soles_rows": int(len(df_sol)),
        "file": str(output_path),
    }
