"""Clasificación del merge en categorías (operaciones).

Reglas:
- RUC nacional = 11 dígitos que empiezan con 10 o 20. Todo lo demás es EXTERIOR.
- Cada fila cae en la PRIMERA operación cuyo ámbito (Nacional/Exterior) y
  moneda (SOL/USD) coinciden con los de la fila. Sin posiciones fijas: depende
  de cómo estén configuradas las operaciones.
- Los tags (ver `_posicion_por_tags`) prevalecen sobre esta regla por defecto.
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


def _posicion_objetivo(ruc, moneda, operaciones) -> int | None:
    """Posición (1-based) de la primera operación cuyo ámbito y moneda
    coinciden con la fila. Config-driven: no usa posiciones fijas."""
    row_ambito = _ambito_fila(ruc)
    row_moneda = str(moneda).strip().upper()
    for i, op in enumerate(operaciones):
        if str(op.ambito).strip() != row_ambito:
            continue
        if str(op.moneda).strip().upper() != row_moneda:
            continue
        return i + 1
    return None


def _ambito_fila(ruc) -> str:
    return "Nacional" if es_ruc_nacional(ruc) else "Exterior"


# Tag especial que matchea contra la columna TIPO (ej. "tipo:02" para recibos
# por honorarios), en vez de buscar el texto en toda la fila.
_TIPO_TAG_RE = re.compile(r"^tipo\s*[:=]\s*(\w+)$", re.IGNORECASE)


def _norm_tipo(v) -> str:
    s = re.sub(r"\.0$", "", str(v).strip())
    return "0" + s if s.isdigit() and len(s) == 1 else s


def _posicion_por_tags(
    contenido: str, row_moneda: str, row_tipo: str, operaciones
) -> int | None:
    """Si algún tag de una categoría (con la misma moneda) coincide, devuelve su
    posición. Prevalece sobre lo demás e IGNORA el ámbito, para que un RUC
    etiquetado se respete 'sí o sí'. Un tag 'tipo:NN' matchea contra la columna
    TIPO (ej. 'tipo:02' = recibos por honorarios); el resto busca el texto en el
    contenido de la fila."""
    for i, op in enumerate(operaciones):
        if str(op.moneda).strip().upper() != row_moneda:
            continue
        for tag in op.tags or []:
            t = str(tag).strip()
            if not t:
                continue
            m = _TIPO_TAG_RE.match(t)
            if m:
                if _norm_tipo(row_tipo) == _norm_tipo(m.group(1)):
                    return i + 1
            elif t.lower() in contenido:
                return i + 1
    return None


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
        pos = _posicion_objetivo(ruc, moneda, operaciones)
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
    tipo_col = _resolve_col(df, "TIPO")
    fecha_col = _resolve_fecha_col(df)
    iso_list = _fechas_iso(df, fecha_col) if fecha_col else None
    n = len(operaciones)

    filas = df.to_dict(orient="records")
    for idx, rec in enumerate(filas):
        ruc = rec.get(ruc_col, "") if ruc_col else ""
        moneda = rec.get(moneda_col, "") if moneda_col else ""
        tipo = rec.get(tipo_col, "") if tipo_col else ""
        contenido = " ".join(str(v) for v in rec.values()).lower()
        row_moneda = str(moneda).strip().upper()

        # Los tags prevalecen (respetando la moneda; el ámbito no bloquea).
        pos = _posicion_por_tags(contenido, row_moneda, tipo, operaciones)
        if pos is None:
            pos = _posicion_objetivo(ruc, moneda, operaciones)

        rec["__pos"] = pos if (pos and pos <= n) else None
        if iso_list is not None:
            rec["__fec_vcto"] = iso_list[idx]

    operaciones_out = [
        {
            "pos": i + 1,
            "texto": op.texto,
            "moneda": op.moneda,
            "ambito": op.ambito,
            "respeta_filtro": bool(
                op.respeta_filtro if op.respeta_filtro is not None else True
            ),
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
