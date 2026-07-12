"""Merge del combinado de Proveedores con el Reporteador limpiado.

- Base: archivo combinado de Proveedores (USD + SOL) — es el que "manda".
- Se le hace un left join con las columnas del Reporteador limpiado:
  NUMERO, ORD_COMPRA, PRODUCTO, REGISTRO, RUC, DETRACCION.
- Llaves del join: RUC y NUMERO.
- El resultado conserva TODAS las filas de Proveedores (y solo esas).
"""

from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.services import proveedores_service, reporteador_service
from app.services.excel_utils import ProcesamientoError, write_xlsx

AVANCE_FILENAME = "merge_avance.xlsx"

# Columnas del reporteador limpio que se traen al merge (RUC y NUMERO son llaves).
_REPORTEADOR_COLUMNS = [
    "NUMERO",
    "ORD_COMPRA",
    "PRODUCTO",
    "REGISTRO",
    "RUC",
    "DETRACCION",
]
_KEYS = ["RUC", "NUMERO"]

# Nombres aceptados en Proveedores para cada columna llave (se normalizan).
_KEY_ALIASES = {
    "RUC": ("RUC", "R.U.C.", "R.U.C"),
    "NUMERO": (
        "NUMERO",
        "NÚMERO",
        "N° DOCUMENTO",
        "N°DOCUMENTO",
        "NRO DOCUMENTO",
        "N DOCUMENTO",
        "NUMERO DOCUMENTO",
        "NÚMERO DOCUMENTO",
    ),
}


def avance_path() -> Path:
    return Path(settings.REPORTS_DIR) / AVANCE_FILENAME


def _normalize(name: str) -> str:
    # Colapsa espacios, mayúsculas y unifica el símbolo ordinal/grado.
    return " ".join(str(name).split()).upper().replace("º", "°")


def _resolve_key(df: pd.DataFrame, canonical: str) -> str | None:
    wanted = {_normalize(alias) for alias in _KEY_ALIASES[canonical]}
    for col in df.columns:
        if _normalize(col) in wanted:
            return col
    return None


def merge_dataframes(
    proveedores: pd.DataFrame, reporteador: pd.DataFrame
) -> pd.DataFrame:
    ruc_col = _resolve_key(proveedores, "RUC")
    numero_col = _resolve_key(proveedores, "NUMERO")
    missing = [
        name
        for name, col in (("RUC", ruc_col), ("NUMERO", numero_col))
        if col is None
    ]
    if missing:
        raise ProcesamientoError(
            "El combinado de proveedores no tiene la(s) columna(s) llave: "
            + ", ".join(missing)
        )

    proveedores = proveedores.rename(columns={ruc_col: "RUC", numero_col: "NUMERO"})
    reporteador = reporteador.copy()

    # Asegurar que existan todas las columnas esperadas del reporteador.
    for col in _REPORTEADOR_COLUMNS:
        if col not in reporteador.columns:
            reporteador[col] = ""

    # Normalizar llaves (evita fallos por espacios sobrantes).
    for df in (proveedores, reporteador):
        for key in _KEYS:
            df[key] = df[key].astype(str).str.strip()

    # Una sola fila del reporteador por llave, para no multiplicar las de
    # proveedores en el left join (el conteo final = filas de proveedores).
    reporteador_subset = reporteador[_REPORTEADOR_COLUMNS].drop_duplicates(
        subset=_KEYS, keep="first"
    )

    merged = proveedores.merge(
        reporteador_subset,
        on=_KEYS,
        how="left",
        suffixes=("", "_reporteador"),
    )

    # DETRACCION: completar con 0 los vacíos (p. ej. filas que no cruzaron).
    detraccion = merged["DETRACCION"].fillna("").astype(str).str.strip()
    merged["DETRACCION"] = detraccion.where(detraccion != "", "0")

    return merged


def process_merge() -> dict:
    rep_path = reporteador_service.avance_path()
    prov_path = proveedores_service.avance_path()
    if not rep_path.exists():
        raise ProcesamientoError("Primero procesa el Reporteador.")
    if not prov_path.exists():
        raise ProcesamientoError("Primero procesa los Proveedores.")

    reporteador = pd.read_excel(rep_path, dtype=str).fillna("")
    proveedores = pd.read_excel(prov_path, dtype=str).fillna("")

    merged = merge_dataframes(proveedores, reporteador)

    output_path = avance_path()
    write_xlsx(merged, output_path, sheet_name="Merge")
    return {"rows": int(len(merged)), "file": str(output_path)}
