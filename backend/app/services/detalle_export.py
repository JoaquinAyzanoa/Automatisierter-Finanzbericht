"""Genera el Excel de descarga rellenando la plantilla del usuario
(app/resources/plantilla.xlsx), conservando exactamente sus colores, layout,
secciones fijas (Agentes de Aduanas, Pagos al Personal, Seguros) y fórmulas.

Solo se inyectan los datos en las secciones 'Operación N' (por posición), y en
el Resumen se rellenan los importes de 'I. PAGOS A REALIZAR'. La categoría
'Otros' (sin categoría) NO se incluye.

La plantilla tiene 19 columnas (col 1 = PROVEEDOR, col 2 = TIPO, ...). En la
salida se INSERTA una columna 'RUC' en la posición 2 (entre PROVEEDOR y TIPO),
de modo que todas las columnas de la plantilla ≥ 2 se desplazan +1. El mapeo
src (plantilla) -> dst (salida) es: col 1 -> 1; col c≥2 -> c+1; y la col 2 de
la salida es la nueva 'RUC'. Las fórmulas se trasladan con Translator (fila y
columna) al copiar; como ninguna referencia apunta a la columna A, el
desplazamiento uniforme +1 de columna es correcto.

Columnas calculadas (supuestos):
- % DET = columna DETRACCION (tasa).  DET = IMPORTE * % DET / 100.  Neto = SALDO - DET - RET.
"""

import re
from copy import copy
from datetime import date, datetime
from pathlib import Path

import openpyxl
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.formula.translate import Translator
from openpyxl.styles import Alignment, Font
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.worksheet.cell_range import CellRange
from openpyxl.worksheet.worksheet import Worksheet

from app.services import sharepoint

# --- Columnas de la SALIDA (dst), ya con la columna RUC insertada en la 2 ---
_COL_RUC = 2
# Columna SUSTENTO / LINK FACTURA (donde va el hipervínculo al PDF).
_COL_LINK = 20
_LINK_FONT = Font(color="0563C1", underline="single")

# Columna DET: formato contable con 2 decimales (cero -> guion).
_COL_DET = 13
_DET_FMT = "_-* #,##0.00_-;\\-* #,##0.00_-;_-* \\-??_-;_-@_-"

# Porcentaje con guion en el cero: "12 %" / "-" (para %DET y %RET).
_PCT_FMT = '0 %;-0 %;"-"'

_PLANTILLA = Path(__file__).resolve().parent.parent / "resources" / "plantilla.xlsx"
_DATETIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}:\d{2}")
_OPERACION_RE = re.compile(r"^\s*Operaci.n\s+(\d+)", re.IGNORECASE)

# Aseguradoras con las que se trabaja hoy (sección 'PAGOS SEGUROS'). La
# plantilla trae una lista más larga; aquí se reemplaza por estas filas.
_SEGUROS_PROVEEDORES = [
    "RIMAC S.A. ENTIDAD PRESTADORA DE SALUD",
    "RIMAC SEGUROS Y REASEGUROS",
]

# Detalle (SALIDA): columna (1-based) -> clave de texto en los datos.
_TXT = {
    1: "PROVEEDOR", 2: "RUC", 3: "TIPO", 4: "NUMERO",
    5: "FEC REGISTRO", 6: "FECHA DOC.", 7: "FEC. VCTO",
    17: "PRODUCTO", 18: "ORD_COMPRA", 19: "REGISTRO", 20: "REGISTRO",
}
_FECHA_COLS = {5, 6, 7}


def _num(value) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


_FECHA_FMT = "yyyy-mm-dd"

# Plazos de crédito establecidos (días). La resta FEC.VCTO - FEC.DOC se ajusta
# al más cercano de esta lista (p. ej. 6 -> 7, 31 -> 30, 14 -> 15).
_PLAZOS = [1, 7, 15, 30, 45, 60]
# Puntos de corte: 0 y el punto medio entre cada par consecutivo (redondeado
# hacia arriba), para que LOOKUP devuelva el plazo más cercano.
_PLAZO_CORTES = [0] + [
    (a + b + 1) // 2 for a, b in zip(_PLAZOS, _PLAZOS[1:])
]
_PLAZO_LOOKUP = (
    "{" + ",".join(str(c) for c in _PLAZO_CORTES) + "},"
    "{" + ",".join(str(p) for p in _PLAZOS) + "}"
)


def _fecha(value):
    """Fecha como objeto `date` para que Excel pueda operarla (p. ej. PLAZO).
    Si el valor no es una fecha reconocible, devuelve el texto tal cual."""
    s = "" if value is None else str(value).strip()
    m = _DATETIME_RE.match(s)
    if m:
        s = m.group(1)
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return s


def _norm_ruc(ruc) -> str:
    return re.sub(r"\.0$", "", str(ruc).strip())


def _es_ruc_nacional(ruc) -> bool:
    """RUC nacional: 11 dígitos que empiezan con 10 o 20 (persona natural/jurídica)."""
    r = _norm_ruc(ruc)
    return len(r) == 11 and r.isdigit() and r[:2] in ("10", "20")


def _fmt_tipo(v) -> str:
    """Normaliza el TIPO de comprobante: un solo dígito se rellena a 2 ('1' -> '01')."""
    s = re.sub(r"\.0$", "", str(v).strip())
    return "0" + s if s.isdigit() and len(s) == 1 else s


def _key_prov(f) -> str:
    """Clave para ordenar filas por PROVEEDOR (alfabético, sin distinguir may/min)."""
    return str(f.get("PROVEEDOR", "")).strip().upper()


# Retención de IGV (SUNAT): 3% del IMPORTE en facturas de bienes que superan
# S/ 700 (o su equivalente en dólares). Valores fijos por norma.
_TASA_RETENCION = 3.0
_UMBRAL_RETENCION = 700.0

# Tipo de cambio (S/ por US$) por defecto y su celda en el Resumen.
TIPO_CAMBIO_DEFAULT = 3.5
_CELDA_TIPO_CAMBIO = "C18"


def _pct_retencion(f: dict, ret_cfg: dict | None) -> float:
    """% de retención de una factura (0 si no aplica).

    - Operación sin retención (p. ej. Pagos servicios) -> 0.
    - Proveedor del exterior (RUC no nacional) -> 0: la retención es a bienes
      nacionales; las importaciones (p. ej. Materia Prima Exterior) no aplican.
    - Con detracción (%DET > 0) -> 0: es un servicio, no un bien.
    - Proveedor que es agente de retención -> 0 (excepción configurada).
    - IMPORTE (convertido a soles) que no supera S/ 700 -> 0.
    - En otro caso -> 3%.
    """
    if not ret_cfg or not ret_cfg.get("activo"):
        return 0.0
    if f.get("__pos") in (ret_cfg.get("pos_sin_ret") or set()):
        return 0.0
    if not _es_ruc_nacional(f.get("RUC", "")):
        return 0.0
    if _num(f.get("DETRACCION")) > 0:
        return 0.0
    if _norm_ruc(f.get("RUC", "")) in (ret_cfg.get("rucs") or set()):
        return 0.0
    importe = _num(f.get("IMPORTE"))
    if str(f.get("MONEDA", "")).strip().upper() != "SOL":
        importe *= float(ret_cfg.get("tipo_cambio") or 0)
    return _TASA_RETENCION if importe > _UMBRAL_RETENCION else 0.0


def _clonar_estilo(d, s) -> None:
    if s.has_style:
        d._style = copy(s._style)


def _quitar_negrita(cell) -> None:
    """Quita la negrita de una celda conservando el resto de la fuente."""
    f = cell.font
    if f is not None and f.bold:
        cell.font = Font(
            name=f.name, size=f.size, bold=False, italic=f.italic,
            vertAlign=f.vertAlign, underline=f.underline, strike=f.strike,
            color=f.color,
        )


def _valores_fila(f: dict, ret_cfg: dict | None = None) -> dict:
    """Valores por columna (SALIDA, 1-based) para una fila del Detalle."""
    importe = round(_num(f.get("IMPORTE")), 2)
    pagado = round(_num(f.get("PAGADO")), 2)
    saldo = round(_num(f.get("SALDO")), 2)
    p_det = _num(f.get("DETRACCION"))
    det = round(importe * p_det / 100, 2)
    vals = {i: (_fecha(f.get(k)) if i in _FECHA_COLS else f.get(k, "")) for i, k in _TXT.items()}
    vals[_COL_RUC] = _norm_ruc(f.get("RUC", ""))
    vals[3] = _fmt_tipo(f.get("TIPO", ""))  # TIPO: "1" -> "01"
    # %DET y %RET como fracción (12 -> 0.12) para que Excel muestre "12 %".
    # RET y Neto se escriben como fórmulas (ver _escribir_fila).
    vals.update({8: importe, 9: pagado, 10: saldo, 12: p_det / 100, 13: det})
    vals[14] = _pct_retencion(f, ret_cfg) / 100  # %RET
    return vals


def _neto(f: dict, ret_cfg: dict | None = None) -> float:
    """Neto numérico de una fila, replicando la fórmula del Detalle:
      si DET>0 y |PAGADO-DET|<1  -> SALDO
      si DET>0 y PAGADO=0        -> SALDO-DET
      en otro caso               -> SALDO
    y luego se le resta la retención (RET = %RET * IMPORTE).
    """
    importe = round(_num(f.get("IMPORTE")), 2)
    saldo = round(_num(f.get("SALDO")), 2)
    pagado = round(_num(f.get("PAGADO")), 2)
    det = round(importe * _num(f.get("DETRACCION")) / 100, 2)
    if det > 0 and abs(pagado - det) < 1:
        base = saldo
    elif det > 0 and pagado == 0:
        base = saldo - det
    else:
        base = saldo
    ret = round(importe * _pct_retencion(f, ret_cfg) / 100, 2)
    return round(base - ret, 2)


# Marcador cuando la O/C se consolida por un proveedor relacionado / TIPO 21
# pero no hay una factura del agente en los datos (nombre a mano).
_AGENTE_MANUAL = "Colocar nombre de agente manualmente"

# Tipo de comprobante que, por sí solo, marca una factura como relacionada a un
# agente (va a 'Detalle de agentes' aunque no haya coincidencia de O/C).
_TIPO_AGENTE = "21"


def _tipo(f: dict) -> str:
    return re.sub(r"\.0$", "", str(f.get("TIPO", "")).strip())


def _es_fila_agente(f: dict, ocs_consolidadas: set) -> bool:
    """Una factura va a 'Detalle de agentes' si su O/C está consolidada (tiene un
    agente/proveedor relacionado) o si su TIPO es de agente (21). Si el usuario
    la reasignó manualmente (`__manual`), respeta esa decisión y no va a agentes."""
    if f.get("__manual"):
        return False
    oc = str(f.get("ORD_COMPRA", "")).strip()
    return (bool(oc) and oc in ocs_consolidadas) or _tipo(f) == _TIPO_AGENTE


def _agrupar_agentes(
    filas: list[dict], agente_rucs: list[str], relacionados_rucs: list[str] = None
) -> tuple:
    """Agrupa las facturas que van a 'Detalle de agentes'.

    - Una O/C se consolida (TODAS sus facturas) si incluye un RUC de agente o de
      proveedor relacionado.
    - Además, cualquier factura con TIPO 21 va a agentes por sí sola (aunque su
      O/C no se consolide).

    Devuelve:
      - ocs_consolidadas: set de O/C consolidadas por RUC (para excluir de las
        operaciones normales).
      - nombre_por_oc: O/C -> nombre del agente (o marcador si no hay agente real).
      - ruc_por_oc: O/C -> RUC del agente ("" si no hay agente real).
      - grupos: (O/C, MONEDA) -> lista de filas (O/C "" = facturas TIPO 21 sin O/C).
    """
    agentes = {_norm_ruc(r) for r in (agente_rucs or []) if str(r).strip()}
    relacionados = {_norm_ruc(r) for r in (relacionados_rucs or []) if str(r).strip()}
    disparadores = agentes | relacionados

    # O/C consolidadas (toda la orden) + nombre/ruc del agente real por O/C.
    ocs_consolidadas: set[str] = set()
    agente_nombre_oc: dict[str, str] = {}
    agente_ruc_oc: dict[str, str] = {}
    for f in filas:
        oc = str(f.get("ORD_COMPRA", "")).strip()
        if not oc:
            continue
        ruc = _norm_ruc(f.get("RUC", ""))
        if ruc in disparadores:
            ocs_consolidadas.add(oc)
        if ruc in agentes and oc not in agente_nombre_oc:
            agente_nombre_oc[oc] = str(f.get("PROVEEDOR", "")).strip()
            agente_ruc_oc[oc] = ruc

    # Agrupar todas las filas que van a agentes (por O/C+moneda; sin O/C -> "").
    grupos: dict = {}
    for f in filas:
        if not _es_fila_agente(f, ocs_consolidadas):
            continue
        oc = str(f.get("ORD_COMPRA", "")).strip()
        moneda = str(f.get("MONEDA", "")).strip().upper()
        grupos.setdefault((oc, moneda), []).append(f)

    # Nombre/RUC por O/C: agente real si existe, si no marcador para llenar a mano.
    nombre_por_oc: dict[str, str] = {}
    ruc_por_oc: dict[str, str] = {}
    for oc, _moneda in grupos:
        if oc in agente_nombre_oc:
            nombre_por_oc[oc] = agente_nombre_oc[oc]
            ruc_por_oc[oc] = agente_ruc_oc[oc]
        else:
            nombre_por_oc[oc] = _AGENTE_MANUAL
            ruc_por_oc[oc] = ""

    return ocs_consolidadas, nombre_por_oc, ruc_por_oc, grupos


def _copiar_celda(s, d, src_r: int, dst_r: int, src_col: int, dst_col: int) -> None:
    """Copia estilo y valor de s->d, trasladando fórmulas al nuevo (fila, col)."""
    if s.has_style:
        d._style = copy(s._style)
    v = s.value
    if isinstance(v, str) and v.startswith("=") and (src_r, src_col) != (dst_r, dst_col):
        try:
            v = Translator(
                v, origin=f"{get_column_letter(src_col)}{src_r}"
            ).translate_formula(f"{get_column_letter(dst_col)}{dst_r}")
        except Exception:
            pass  # #REF! u otras fórmulas no trasladables: dejar tal cual
    d.value = v


def _nc(c: int) -> int:
    """Columna src (plantilla) -> columna dst (salida): inserta RUC en la 2."""
    return c if c == 1 else c + 1


def _centrar_horizontal(cell) -> None:
    """Centra horizontalmente una celda conservando el resto de la alineación."""
    a = cell.alignment
    cell.alignment = Alignment(
        horizontal="center", vertical=a.vertical, wrap_text=a.wrap_text,
        text_rotation=a.text_rotation, indent=a.indent,
        shrink_to_fit=a.shrink_to_fit,
    )


# Columnas de datos que van centradas horizontalmente (RUC, TIPO, N° DOCUMENTO,
# FEC. REGISTRO, FEC.DOC, FEC.VCTO), mismo layout en Detalle y Detalle de agentes.
_COLS_CENTRAR = range(2, 8)


def _copiar_fila_desplazada(
    src, dst, src_r, dst_r, ncols_src, ruc_val=None, es_cabecera=False
) -> None:
    """Copia una fila de la plantilla a la salida con el desplazamiento de la
    columna RUC. Rellena la col RUC con `ruc_val` (o 'RUC' si es cabecera)."""
    _copiar_celda(src.cell(src_r, 1), dst.cell(dst_r, 1), src_r, dst_r, 1, 1)
    for c in range(2, ncols_src + 1):
        _copiar_celda(src.cell(src_r, c), dst.cell(dst_r, _nc(c)), src_r, dst_r, c, _nc(c))
    # Columna RUC (2) con el estilo de la columna TIPO (src col 2).
    _clonar_estilo(dst.cell(dst_r, _COL_RUC), src.cell(src_r, 2))
    dst.cell(dst_r, _COL_RUC).value = "RUC" if es_cabecera else ruc_val
    # Los encabezados de columna van centrados horizontalmente.
    if es_cabecera:
        for c in range(1, _COL_LINK + 1):
            _centrar_horizontal(dst.cell(dst_r, c))


def _es_cabecera(ws, r) -> bool:
    v = ws.cell(r, 1).value
    return bool(v) and str(v).strip().upper() == "PROVEEDOR"


def _copiar_anchos(src, dst) -> None:
    for letra, dim in src.column_dimensions.items():
        if not dim.width:
            continue
        try:
            idx = column_index_from_string(letra)
        except Exception:
            continue
        dst.column_dimensions[get_column_letter(_nc(idx))].width = dim.width
    dst.column_dimensions[get_column_letter(_COL_RUC)].width = 16  # RUC


# Anchos de las columnas numéricas del 'Detalle' (para que no salgan "######").
# IMPORTE, PAGADO, SALDO, PLAZO, %DET, DET, %RET, RET, Neto.
_ANCHOS_NUM_DETALLE = {8: 12, 9: 11, 10: 12, 11: 7, 12: 8, 13: 12, 14: 8, 15: 10, 16: 12}


def _detectar_operaciones(ws: Worksheet) -> dict:
    """data_start_row -> (pos, total_row) para cada sección 'Operación N'."""
    secciones: dict = {}
    r = 1
    while r <= ws.max_row:
        a = ws.cell(r, 1).value
        m = _OPERACION_RE.match(str(a)) if a else None
        if m:
            header_row = r + 1
            tr = header_row + 1
            while tr <= ws.max_row and str(ws.cell(tr, 1).value).strip().upper() != "TOTAL":
                tr += 1
            secciones[header_row + 1] = (int(m.group(1)), tr)
            r = tr + 1
        else:
            r += 1
    return secciones


_AGENTE_RE = re.compile(r"AGENTES?\s+DE\s+ADUANAS?\s+(SOL|DOL|D.L)", re.IGNORECASE)


def _detectar_agentes(ws: Worksheet) -> dict:
    """data_start_row -> (moneda, total_row) para 'AGENTES DE ADUANAS SOL/DOL'."""
    secciones: dict = {}
    r = 1
    while r <= ws.max_row:
        a = ws.cell(r, 1).value
        m = _AGENTE_RE.search(str(a)) if a else None
        if m:
            moneda = "SOL" if m.group(1).upper().startswith("SOL") else "USD"
            header_row = r + 1
            tr = header_row + 1
            while tr <= ws.max_row and str(ws.cell(tr, 1).value).strip().upper() != "TOTAL":
                tr += 1
            secciones[header_row + 1] = (moneda, tr)
            r = tr + 1
        else:
            r += 1
    return secciones


_SEGUROS_RE = re.compile(r"PAGOS\s+SEGUROS", re.IGNORECASE)


def _detectar_seguros(ws: Worksheet) -> dict:
    """data_start_row -> total_row para la sección 'PAGOS SEGUROS'."""
    secciones: dict = {}
    r = 1
    while r <= ws.max_row:
        a = ws.cell(r, 1).value
        m = _SEGUROS_RE.search(str(a)) if a else None
        if m:
            header_row = r + 1
            tr = header_row + 1
            while tr <= ws.max_row and str(ws.cell(tr, 1).value).strip().upper() != "TOTAL":
                tr += 1
            secciones[header_row + 1] = tr
            r = tr + 1
        else:
            r += 1
    return secciones


# Columna Neto en la hoja 'Detalle de agentes' (para las fórmulas de enlace).
_COL_NETO_AG = 15


def _ref_agentes(fila: int) -> str:
    """Fórmula que jala el Neto de la hoja 'Detalle de agentes' (columna O)."""
    col = get_column_letter(_COL_NETO_AG)
    return f"=+'Detalle de agentes'!{col}{fila}"


def _escribir_resumen_agente(
    src, estilo_row, dst, r, nombre, ruc, oc, total, ncols_src, ref_row=None
):
    """Fila resumen de la sección Agentes: nombre, RUC y O/C del agente y el
    total (Neto) a depositar. Si se da `ref_row`, el total se enlaza por fórmula
    a la hoja 'Detalle de agentes'; si no, se escribe el monto calculado."""
    _copiar_fila_desplazada(src, dst, estilo_row, r, ncols_src, ruc_val=None)
    for c in range(1, _COL_LINK + 1):
        dst.cell(r, c).value = None
    dst.cell(r, 1).value = nombre      # PROVEEDOR
    dst.cell(r, _COL_RUC).value = ruc  # RUC (del agente de la col A)
    dst.cell(r, 16).value = _ref_agentes(ref_row) if ref_row else total  # Neto (P)
    dst.cell(r, 17).value = nombre     # AGENTE ADUANERO
    dst.cell(r, 18).value = oc         # N° O/C-O/S
    for c in _COLS_CENTRAR:  # RUC y demás columnas de identificación: centradas
        _centrar_horizontal(dst.cell(r, c))
    _centrar_horizontal(dst.cell(r, 18))  # N° O/C-O/S centrado


def _escribir_fila(src, estilo_row, dst, r, fila, ncols_src, sp_cfg, ret_cfg=None) -> None:
    """Escribe una fila de datos del Detalle en `r`, con el estilo (desplazado)
    de `estilo_row`."""
    vals = _valores_fila(fila, ret_cfg)
    _clonar_estilo(dst.cell(r, 1), src.cell(estilo_row, 1))
    dst.cell(r, 1).value = vals.get(1)
    _clonar_estilo(dst.cell(r, _COL_RUC), src.cell(estilo_row, 2))  # RUC (estilo TIPO)
    dst.cell(r, _COL_RUC).value = vals.get(_COL_RUC)
    for c in range(2, ncols_src + 1):
        d = dst.cell(r, _nc(c))
        _clonar_estilo(d, src.cell(estilo_row, c))
        d.value = vals.get(_nc(c))
    for c in _COLS_CENTRAR:  # RUC, TIPO, N° DOC y fechas: centrados
        _centrar_horizontal(dst.cell(r, c))
    _centrar_horizontal(dst.cell(r, 12))  # %DET centrado
    _centrar_horizontal(dst.cell(r, 18))  # N° O/C-O/S centrado
    _centrar_horizontal(dst.cell(r, 19))  # N° Registro centrado
    # Fechas como fecha real (para que PLAZO pueda restarlas).
    for c in _FECHA_COLS:
        if isinstance(vals.get(c), date):
            dst.cell(r, c).number_format = _FECHA_FMT
    # PLAZO (K) = FEC.VCTO (G) - FEC.DOC (F) ajustado al plazo de crédito
    # establecido más cercano; vacío si falta alguna fecha.
    dst.cell(r, 11).value = (
        f'=IF(OR(F{r}="",G{r}=""),"",'
        f'LOOKUP(MAX(0,G{r}-F{r}),{_PLAZO_LOOKUP}))'
    )
    dst.cell(r, 11).number_format = "0"
    _centrar_horizontal(dst.cell(r, 11))
    # DET con dos decimales.
    dst.cell(r, _COL_DET).number_format = _DET_FMT
    # %DET y %RET: porcentaje con guion en el cero (como DET/RET).
    dst.cell(r, 12).number_format = _PCT_FMT
    dst.cell(r, 14).number_format = _PCT_FMT
    # %RET con el mismo borde que %DET (sin el recuadro de "llenar a mano").
    dst.cell(r, 14).border = copy(dst.cell(r, 12).border)
    dst.cell(r, 15).value = f"=ROUND(N{r}*H{r},2)"
    dst.cell(r, 15).number_format = _DET_FMT
    # Neto (fórmula viva): SALDO(J), DET(M), PAGADO(I), RET(O).
    dst.cell(r, 16).value = (
        f"=IF(AND(M{r}>0,ABS(I{r}-M{r})<1),J{r},"
        f"IF(AND(M{r}>0,I{r}=0),J{r}-M{r},J{r}))-O{r}"
    )
    # Hipervínculo al PDF en SUSTENTO (nombre del PDF = registro).
    registro = str(vals.get(_COL_LINK) or "").strip()
    if sp_cfg and registro:
        url = sharepoint.link_factura(
            sp_cfg.get("link_principal"), sp_cfg.get("meses"), registro
        )
        if url:
            cel = dst.cell(r, _COL_LINK)
            cel.hyperlink = url
            cel.font = _LINK_FONT
        else:
            dst.cell(r, _COL_LINK).value = None


_MONEDA_TITULO = {"SOL": "Soles", "USD": "Dólares"}


def _titulo_operacion(pos, texto, moneda) -> str:
    """'Operación N - <texto> - <Soles/Dólares>' según la moneda de la config.
    No duplica la moneda si el texto ya la incluye."""
    texto = (texto or "").strip()
    m = str(moneda or "").strip()
    lbl = _MONEDA_TITULO.get(m.upper(), m)
    partes = [f"Operación {pos}"]
    if texto:
        partes.append(texto)
    if lbl and not texto.lower().endswith(lbl.lower()):
        partes.append(lbl)
    return " - ".join(partes)


def _construir_detalle_sheet(
    wb, grupos, operaciones, fecha_inicio, fecha_final, sp_cfg,
    grupos_agentes=None, nombre_por_oc=None, ruc_por_oc=None, ref_agentes=None,
    ret_cfg=None,
) -> dict:
    src = wb["Detalle"]
    # La plantilla tiene 19 columnas reales (hasta SUSTENTO). La salida tendrá 20
    # (se inserta RUC en la 2).
    ncols = 19
    ops = _detectar_operaciones(src)
    agentes = _detectar_agentes(src)
    seguros = _detectar_seguros(src)
    grupos_agentes = grupos_agentes or {}
    nombre_por_oc = nombre_por_oc or {}
    ruc_por_oc = ruc_por_oc or {}
    ref_agentes = ref_agentes or {"oc": {}, "moneda": {}}
    # Texto/moneda actuales de cada operación (config manda sobre la plantilla).
    op_texto = {o["pos"]: o.get("texto", "") for o in operaciones}
    op_moneda = {o["pos"]: o.get("moneda", "") for o in operaciones}

    dst = wb.create_sheet("__detalle_tmp__")
    _copiar_anchos(src, dst)
    # Anchos fijos para las columnas numéricas (evita "######" en DET, etc.).
    for c, w in _ANCHOS_NUM_DETALLE.items():
        dst.column_dimensions[get_column_letter(c)].width = w

    row_map: dict = {}
    total_rows: dict = {}   # pos -> fila TOTAL (destino) de esa operación
    total_merges: list = []
    dst_r = 1
    src_r = 1
    while src_r <= src.max_row:
        if src_r in ops:
            pos, total_row = ops[src_r]
            filas = sorted(grupos.get(pos, []), key=_key_prov)
            estilo_row = src_r  # fila de datos modelo (estilos)
            data_ini = dst_r
            if filas:
                alto = src.row_dimensions[estilo_row].height
                for f in filas:
                    _escribir_fila(src, estilo_row, dst, dst_r, f, ncols, sp_cfg, ret_cfg)
                    if alto:
                        dst.row_dimensions[dst_r].height = alto
                    dst_r += 1
            else:
                # Sin datos: conservar las filas en blanco de la plantilla.
                for rr in range(src_r, total_row):
                    _copiar_fila_desplazada(src, dst, rr, dst_r, ncols)
                    if src.row_dimensions[rr].height:
                        dst.row_dimensions[dst_r].height = src.row_dimensions[rr].height
                    dst_r += 1
            data_fin = dst_r - 1
            # Fila TOTAL (estilo de la plantilla) con Neto (col P) sumado.
            _copiar_fila_desplazada(src, dst, total_row, dst_r, ncols)
            if src.row_dimensions[total_row].height:
                dst.row_dimensions[dst_r].height = src.row_dimensions[total_row].height
            dst.cell(dst_r, 16).value = f"=SUM(P{data_ini}:P{data_fin})"
            total_merges.append(dst_r)
            total_rows[pos] = dst_r
            dst_r += 1
            src_r = total_row + 1
        elif src_r in agentes:
            # Sección 'AGENTES DE ADUANAS SOL/DOL': una fila resumen por O/C
            # (agente, RUC, N° O/C-O/S y total a depositar) de esa moneda.
            moneda, total_row = agentes[src_r]
            estilo_row = src_r
            resumen = sorted(
                ((oc, filas) for (oc, mon), filas in grupos_agentes.items()
                 if mon == moneda),
                key=lambda x: x[0],
            )
            data_ini = dst_r
            if resumen:
                alto = src.row_dimensions[estilo_row].height
                for oc, filas in resumen:
                    total = round(sum(_neto(f, ret_cfg) for f in filas), 2)
                    _escribir_resumen_agente(
                        src, estilo_row, dst, dst_r,
                        nombre_por_oc.get(oc, ""), ruc_por_oc.get(oc, ""),
                        oc, total, ncols,
                        ref_agentes["oc"].get((oc, moneda)),
                    )
                    if alto:
                        dst.row_dimensions[dst_r].height = alto
                    dst_r += 1
            else:
                for rr in range(src_r, total_row):
                    _copiar_fila_desplazada(src, dst, rr, dst_r, ncols)
                    if src.row_dimensions[rr].height:
                        dst.row_dimensions[dst_r].height = src.row_dimensions[rr].height
                    dst_r += 1
            data_fin = dst_r - 1
            _copiar_fila_desplazada(src, dst, total_row, dst_r, ncols)
            if src.row_dimensions[total_row].height:
                dst.row_dimensions[dst_r].height = src.row_dimensions[total_row].height
            if resumen:
                ref_total = ref_agentes["moneda"].get(moneda)
                # El TOTAL de la sección jala el 'TOTAL <moneda>' del Detalle de
                # agentes; si no hay referencia, suma las filas resumen locales.
                dst.cell(dst_r, 16).value = (
                    _ref_agentes(ref_total) if ref_total
                    else f"=SUM(P{data_ini}:P{data_fin})"
                )
            total_merges.append(dst_r)
            dst_r += 1
            src_r = total_row + 1
        elif src_r in seguros:
            # Sección 'PAGOS SEGUROS': se emiten solo las aseguradoras vigentes
            # (la plantilla trae una lista más larga), con el estilo de la fila
            # modelo, y luego la fila TOTAL.
            total_row = seguros[src_r]
            estilo_row = src_r
            alto = src.row_dimensions[estilo_row].height
            for nombre in _SEGUROS_PROVEEDORES:
                _copiar_fila_desplazada(src, dst, estilo_row, dst_r, ncols)
                dst.cell(dst_r, 1).value = nombre
                if alto:
                    dst.row_dimensions[dst_r].height = alto
                dst_r += 1
            _copiar_fila_desplazada(src, dst, total_row, dst_r, ncols)
            if src.row_dimensions[total_row].height:
                dst.row_dimensions[dst_r].height = src.row_dimensions[total_row].height
            total_merges.append(dst_r)
            dst_r += 1
            src_r = total_row + 1
        else:
            _copiar_fila_desplazada(
                src, dst, src_r, dst_r, ncols, es_cabecera=_es_cabecera(src, src_r)
            )
            if src.row_dimensions[src_r].height:
                dst.row_dimensions[dst_r].height = src.row_dimensions[src_r].height
            # Si es un título "Operación N", re-rotularlo con el texto actual de
            # la configuración (la plantilla puede tener nombres desactualizados).
            a = src.cell(src_r, 1).value
            m = _OPERACION_RE.match(str(a)) if a else None
            if m:
                pos = int(m.group(1))
                dst.cell(dst_r, 1).value = _titulo_operacion(
                    pos, op_texto.get(pos), op_moneda.get(pos)
                )
            row_map[src_r] = dst_r
            dst_r += 1
            src_r += 1

    # Operaciones que existen en los datos pero no en la plantilla (p. ej. una
    # 9ª categoría creada en Configuración): se agregan como secciones nuevas al
    # final, copiando el estilo de la última operación de la plantilla.
    plantilla_pos = {p for (p, _tr) in ops.values()}
    extra = sorted(p for p in grupos if p not in plantilla_pos)
    if extra:
        modelo_ds = max(ops)                      # última operación de la plantilla
        m_total = ops[modelo_ds][1]
        m_titulo, m_header, m_data = modelo_ds - 2, modelo_ds - 1, modelo_ds
        for pos in extra:
            filas = sorted(grupos[pos], key=_key_prov)
            dst_r += 1  # fila en blanco de separación
            # Título.
            _copiar_fila_desplazada(src, dst, m_titulo, dst_r, ncols)
            dst.cell(dst_r, 1).value = _titulo_operacion(
                pos, op_texto.get(pos), op_moneda.get(pos)
            )
            dst_r += 1
            # Cabecera.
            _copiar_fila_desplazada(src, dst, m_header, dst_r, ncols, es_cabecera=True)
            dst_r += 1
            # Datos.
            data_ini = dst_r
            alto = src.row_dimensions[m_data].height
            for f in filas:
                _escribir_fila(src, m_data, dst, dst_r, f, ncols, sp_cfg, ret_cfg)
                if alto:
                    dst.row_dimensions[dst_r].height = alto
                dst_r += 1
            data_fin = dst_r - 1
            # TOTAL.
            _copiar_fila_desplazada(src, dst, m_total, dst_r, ncols)
            if src.row_dimensions[m_total].height:
                dst.row_dimensions[dst_r].height = src.row_dimensions[m_total].height
            dst.cell(dst_r, 16).value = f"=SUM(P{data_ini}:P{data_fin})"
            dst.merge_cells(start_row=dst_r, start_column=1, end_row=dst_r, end_column=15)
            total_rows[pos] = dst_r
            dst_r += 1

    # Merges verbatim (de filas copiadas tal cual), con columnas desplazadas.
    for mc in list(src.merged_cells.ranges):
        if mc.min_row in row_map and mc.max_row in row_map:
            dst.merge_cells(
                start_row=row_map[mc.min_row], start_column=_nc(mc.min_col),
                end_row=row_map[mc.max_row], end_column=_nc(mc.max_col),
            )
    # Merges de las filas TOTAL de las secciones Operación/Agentes (A:O).
    for tr in total_merges:
        dst.merge_cells(start_row=tr, start_column=1, end_row=tr, end_column=15)

    # Título con el rango de fechas.
    rango = ""
    if fecha_inicio or fecha_final:
        rango = f" {fecha_inicio or ''}{' a ' + fecha_final if fecha_final else ''}".rstrip()
    dst.cell(1, 1).value = f"PAGOS PROVEEDORES{rango}"

    # Reemplazar la hoja Detalle por la reconstruida, en la misma posición.
    pos_idx = wb.sheetnames.index("Detalle")
    del wb["Detalle"]
    dst.title = "Detalle"
    wb.move_sheet("Detalle", offset=pos_idx - wb.sheetnames.index("Detalle"))
    return total_rows


# Banda 'ESTADO DE LIQUIDEZ' del Resumen (cabecera + valores) que se mueve al
# final de la hoja, después de la sección V.
_RESUMEN_BANDA = (4, 5)
_RESUMEN_NCOLS = 4
# Alto de la fila de valores de la banda (para que el texto del estado, que va
# en dos líneas, se lea completo).
_ALTO_BANDA_ESTADO = 32.5
# Tamaños de fuente de esa fila: la plantilla traía 9 / 16 / 17 / 17 (se veían
# desparejos). El texto del estado va menor porque ocupa dos líneas.
_TAM_BANDA_TEXTO = 11
_TAM_BANDA_MONTOS = 16


def _trasladar_formula(valor, col: str, desde: int, hasta: int):
    """Traslada una fórmula de la fila `desde` a la fila `hasta` (misma columna)."""
    if not (isinstance(valor, str) and valor.startswith("=")) or desde == hasta:
        return valor
    try:
        return Translator(valor, origin=f"{col}{desde}").translate_formula(
            f"{col}{hasta}"
        )
    except Exception:
        return valor


def _mover_banda_liquidez(ws) -> None:
    """Mueve la banda 'ESTADO DE LIQUIDEZ' (filas 4-5) al final del Resumen y
    ELIMINA las filas 3-5 (la separadora de arriba + la banda), igual que si se
    borraran a mano en Excel.

    Al borrar filas las de abajo suben `n`; openpyxl no ajusta las fórmulas ni
    los merges, así que se trasladan/rearman a mano. Las fórmulas de la banda
    también se ajustan, porque sus referencias (D18, D25, C31, D35-D37) subieron
    lo mismo.

    Debe ejecutarse ANTES de reescribir las fórmulas de 'Operación N' (que
    apuntan a la hoja Detalle), para que esas se escriban ya con la fila final.
    """
    r_ini, r_fin = _RESUMEN_BANDA
    if not str(ws.cell(r_ini, 1).value or "").strip().upper().startswith(
        "ESTADO DE LIQUIDEZ"
    ):
        return  # la plantilla ya no tiene la banda arriba: nada que mover

    r_borrar = r_ini - 1               # fila en blanco que va encima de la banda
    n = (r_fin - r_borrar) + 1         # filas a borrar: separadora + banda

    banda = [
        {
            "row": r,
            "alto": ws.row_dimensions[r].height,
            "celdas": [
                (
                    ws.cell(r, c).value,
                    copy(ws.cell(r, c)._style) if ws.cell(r, c).has_style else None,
                )
                for c in range(1, _RESUMEN_NCOLS + 1)
            ],
        }
        for r in range(r_ini, r_fin + 1)
    ]

    # Borrar la banda y su separador: todo lo de abajo sube n filas.
    # openpyxl no ajusta merges ni formato condicional al borrar filas (quedarían
    # desfasados: taparían contenido o pintarían celdas equivocadas). Se guardan,
    # se limpian y se rearman con las filas nuevas.
    merges = [
        (m.min_row, m.min_col, m.max_row, m.max_col)
        for m in list(ws.merged_cells.ranges)
    ]
    for m in list(ws.merged_cells.ranges):
        ws.unmerge_cells(str(m))

    cond = [(str(cf.sqref), list(cf.rules)) for cf in ws.conditional_formatting]
    ws.conditional_formatting = ConditionalFormattingList()

    ws.delete_rows(r_borrar, n)
    for row in ws.iter_rows(min_row=r_borrar, max_row=ws.max_row):
        for cel in row:
            v = cel.value
            if not (isinstance(v, str) and v.startswith("=")):
                continue
            nuevo = _trasladar_formula(
                v, get_column_letter(cel.column), cel.row + n, cel.row
            )
            if nuevo != v:
                cel.value = nuevo

    for min_r, min_c, max_r, max_c in merges:
        if max_r < r_borrar:
            f1, f2 = min_r, max_r          # arriba de lo borrado: sin cambio
        elif min_r >= r_borrar + n:
            f1, f2 = min_r - n, max_r - n  # abajo: sube n filas
        else:
            continue                       # estaba dentro de lo borrado
        ws.merge_cells(start_row=f1, start_column=min_c, end_row=f2, end_column=max_c)

    # Escribir la banda al final, dejando una fila en blanco de separación.
    ultima = max(
        (
            r
            for r in range(1, ws.max_row + 1)
            if any(
                ws.cell(r, c).value not in (None, "")
                for c in range(1, _RESUMEN_NCOLS + 1)
            )
        ),
        default=ws.max_row,
    )
    destino = ultima + 2
    ultima_i = len(banda) - 1
    for i, fila in enumerate(banda):
        r = destino + i
        # La última fila de la banda (los valores) lleva un alto mayor.
        alto = _ALTO_BANDA_ESTADO if i == ultima_i else fila["alto"]
        if alto:
            ws.row_dimensions[r].height = alto
        for c, (valor, estilo) in enumerate(fila["celdas"], start=1):
            cel = ws.cell(r, c)
            # Sus referencias también subieron n filas.
            cel.value = _trasladar_formula(
                valor, get_column_letter(c), fila["row"], fila["row"] - n
            )
            if estilo is not None:
                cel._style = estilo
            # Uniformar el tamaño de fuente de la fila de valores (venía disparejo).
            if i == ultima_i:
                f = cel.font
                cel.font = Font(
                    name=f.name,
                    size=_TAM_BANDA_TEXTO if c == 1 else _TAM_BANDA_MONTOS,
                    bold=f.b, italic=f.i, color=f.color,
                    vertAlign=f.vertAlign, underline=f.underline, strike=f.strike,
                )

    # Rearmar el formato condicional con las filas nuevas.
    def _fila_nueva(r: int):
        if r_ini <= r <= r_fin:
            return destino + (r - r_ini)   # estaba en la banda: se fue al final
        if r < r_borrar:
            return r                       # arriba de lo borrado
        if r >= r_borrar + n:
            return r - n                   # abajo: sube n
        return None                        # fila borrada

    for sqref, reglas in cond:
        rangos = []
        for parte in str(sqref).split():
            cr = CellRange(parte)
            f1, f2 = _fila_nueva(cr.min_row), _fila_nueva(cr.max_row)
            if f1 is None or f2 is None:
                continue
            rangos.append(
                f"{get_column_letter(cr.min_col)}{f1}:"
                f"{get_column_letter(cr.max_col)}{f2}"
            )
        if not rangos:
            continue
        for regla in reglas:
            ws.conditional_formatting.add(" ".join(rangos), regla)


# Anchos fijos de columnas del Resumen:
# A = 'Banco/Concepto', B = 'Operación', C = 'Moneda', D = 'Importe'.
_ANCHOS_RESUMEN = {"A": 32, "B": 41.5, "C": 35, "D": 24}


def _ajustar_ancho_operacion(ws) -> None:
    """Fija los anchos de columna del Resumen."""
    for col, ancho in _ANCHOS_RESUMEN.items():
        ws.column_dimensions[col].width = ancho


def _rellenar_resumen(wb, total_rows: dict, operaciones: list) -> None:
    if "Resumen" not in wb.sheetnames:
        return
    ws = wb["Resumen"]
    # Primero se reacomoda la hoja (mover banda + borrar filas), y recién luego
    # se escriben las fórmulas hacia Detalle, ya en su fila definitiva.
    _mover_banda_liquidez(ws)
    op_texto = {o["pos"]: o.get("texto", "") for o in operaciones}
    op_moneda = {o["pos"]: o.get("moneda", "") for o in operaciones}
    # En 'I. PAGOS A REALIZAR' cada fila tiene la etiqueta 'Operación N' en col B
    # y una fórmula en col D que apunta al TOTAL de esa operación en Detalle.
    # Re-rotulamos la etiqueta con el nombre actual (la plantilla puede tenerlo
    # desactualizado) y re-apuntamos la fórmula a la nueva fila TOTAL. El Neto
    # está ahora en la columna P del Detalle (antes O, por la columna RUC).
    for r in range(1, ws.max_row + 1):
        b = ws.cell(r, 2).value
        m = _OPERACION_RE.match(str(b)) if b else None
        if m:
            pos = int(m.group(1))
            ws.cell(r, 2).value = _titulo_operacion(
                pos, op_texto.get(pos), op_moneda.get(pos)
            )
            if pos in total_rows:
                ws.cell(r, 4).value = f"=+Detalle!P{total_rows[pos]}"

    # La columna de 'Operación' se ajusta a las etiquetas ya reescritas.
    _ajustar_ancho_operacion(ws)


# Hoja 'Detalle de agentes' (SALIDA): columna -> clave de texto. Layout propio
# (SIN la columna PLAZO del Detalle) con la columna RUC insertada en la 2:
# 1 PROV, 2 RUC, 3 TIPO, 4 NUMERO, 5-7 fechas, 8 IMPORTE, 9 PAGADO, 10 SALDO,
# 11 %DET, 12 DET, 13 %RET, 14 RET, 15 Neto, 16 PRODUCTO, 17 AGENTE, 18 O/C, 20 LINK.
_TXT_AG = {
    1: "PROVEEDOR", 2: "RUC", 3: "TIPO", 4: "NUMERO",
    5: "FEC REGISTRO", 6: "FECHA DOC.", 7: "FEC. VCTO",
    16: "PRODUCTO", 18: "ORD_COMPRA", 19: "REGISTRO", 20: "REGISTRO",
}


def _valores_fila_ag(f: dict, ret_cfg: dict | None = None) -> dict:
    """Valores por columna (SALIDA) para una fila de 'Detalle de agentes'."""
    importe = round(_num(f.get("IMPORTE")), 2)
    pagado = round(_num(f.get("PAGADO")), 2)
    saldo = round(_num(f.get("SALDO")), 2)
    p_det = _num(f.get("DETRACCION"))
    det = round(importe * p_det / 100, 2)
    vals = {
        i: (_fecha(f.get(k)) if i in _FECHA_COLS else f.get(k, ""))
        for i, k in _TXT_AG.items()
    }
    vals[_COL_RUC] = _norm_ruc(f.get("RUC", ""))
    vals[3] = _fmt_tipo(f.get("TIPO", ""))  # TIPO: "1" -> "01"
    vals.update({8: importe, 9: pagado, 10: saldo, 11: p_det / 100, 12: det})
    vals[13] = _pct_retencion(f, ret_cfg) / 100  # %RET
    return vals


def _escribir_fila_agente(
    src, estilo_row, dst, r, f, ncols_src, sp_cfg, agente, ret_cfg=None
):
    """Escribe una factura en la hoja 'Detalle de agentes' (con columna RUC)."""
    vals = _valores_fila_ag(f, ret_cfg)
    _clonar_estilo(dst.cell(r, 1), src.cell(estilo_row, 1))
    dst.cell(r, 1).value = vals.get(1)
    _clonar_estilo(dst.cell(r, _COL_RUC), src.cell(estilo_row, 2))  # RUC (estilo TIPO)
    dst.cell(r, _COL_RUC).value = vals.get(_COL_RUC)
    for c in range(2, ncols_src + 1):
        d = dst.cell(r, _nc(c))
        _clonar_estilo(d, src.cell(estilo_row, c))
        d.value = vals.get(_nc(c))
    dst.cell(r, 12).number_format = _DET_FMT                       # DET
    for c in _FECHA_COLS:  # fechas como fecha real
        if isinstance(vals.get(c), date):
            dst.cell(r, c).number_format = _FECHA_FMT
    dst.cell(r, 11).number_format = _PCT_FMT                       # %DET: 0 -> "-"
    dst.cell(r, 13).number_format = _PCT_FMT                       # %RET: 0 -> "-"
    dst.cell(r, 13).border = copy(dst.cell(r, 11).border)         # %RET como %DET
    dst.cell(r, 14).value = f"=ROUND(M{r}*H{r},2)"                 # RET = %RET*IMPORTE (2 dec)
    dst.cell(r, 14).number_format = _DET_FMT
    dst.cell(r, 15).value = f"=J{r}-L{r}-N{r}"                     # Neto = SALDO-DET-RET
    if agente:
        dst.cell(r, 17).value = agente                            # AGENTE ADUANERO
    # Los datos de relleno no van en negrita (la fila modelo de la plantilla la trae).
    for c in range(1, _COL_LINK + 1):
        _quitar_negrita(dst.cell(r, c))
    for c in _COLS_CENTRAR:  # RUC, TIPO, N° DOC y fechas: centrados
        _centrar_horizontal(dst.cell(r, c))
    _centrar_horizontal(dst.cell(r, 11))  # %DET centrado
    _centrar_horizontal(dst.cell(r, 18))  # N° O/C-O/S centrado
    _centrar_horizontal(dst.cell(r, 19))  # N° Registro centrado
    registro = str(f.get("REGISTRO") or "").strip()
    if sp_cfg and registro:
        url = sharepoint.link_factura(
            sp_cfg.get("link_principal"), sp_cfg.get("meses"), registro
        )
        if url:
            cel = dst.cell(r, _COL_LINK)
            cel.hyperlink = url
            cel.font = _LINK_FONT


_MONEDA_ETIQUETA = {"SOL": "SOLES", "USD": "DOLARES"}

# Anchos de la hoja 'Detalle de agentes'.
# - Fijos: columnas numéricas / de fórmula / fechas.
_ANCHOS_FIJOS_AG = {
    2: 16, 3: 6, 5: 13, 6: 13, 7: 13, 8: 12, 9: 11, 10: 12,
    11: 8, 12: 12, 13: 8, 14: 11, 15: 12, 20: 14,
}
# - Auto (por contenido) con (mínimo, máximo): columnas de texto.
_ANCHOS_AUTO_AG = {
    1: (18, 45), 4: (12, 22), 16: (16, 55), 17: (18, 45), 18: (11, 18), 19: (12, 16),
}


def _ajustar_anchos_agentes(dst, max_row: int) -> None:
    """Ajusta los anchos de 'Detalle de agentes' para que los datos se vean
    completos (auto por contenido en texto; fijo en numéricas)."""
    for c, w in _ANCHOS_FIJOS_AG.items():
        dst.column_dimensions[get_column_letter(c)].width = w
    for c, (lo, hi) in _ANCHOS_AUTO_AG.items():
        maxlen = 0
        for r in range(1, max_row + 1):
            v = dst.cell(r, c).value
            if v is None or (isinstance(v, str) and v.startswith("=")):
                continue
            maxlen = max(maxlen, len(str(v)))
        dst.column_dimensions[get_column_letter(c)].width = min(max(maxlen + 2, lo), hi)


def _construir_detalle_agentes_sheet(
    wb, grupos_agentes, nombre_por_oc, sp_cfg, ret_cfg=None
):
    """Reconstruye la hoja 'Detalle de agentes' con el detalle de todas las
    facturas agrupadas por O/C. Se separa por moneda (SOLES primero, luego
    DÓLARES), con un subtotal por O/C y un total por moneda.

    Devuelve las filas (en la columna Neto = O) de cada subtotal para que el
    'Detalle' pueda enlazarlas con fórmulas:
      {"oc": {(oc, moneda): fila}, "moneda": {moneda: fila_total}}
    """
    ref = {"oc": {}, "moneda": {}}
    if "Detalle de agentes" not in wb.sheetnames:
        return ref
    src = wb["Detalle de agentes"]
    ncols = 19
    ncols_dst = _nc(ncols)
    header_row, data_style, subtotal_style = 2, 3, 6

    dst = wb.create_sheet("__agentes_tmp__")
    _copiar_anchos(src, dst)

    # Agrupar por moneda: SOLES primero, DÓLARES después, resto al final.
    por_moneda: dict[str, dict] = {}
    for (oc, moneda), filas in grupos_agentes.items():
        por_moneda.setdefault(moneda, {})[oc] = filas
    orden = ["SOL", "USD"]
    monedas = [m for m in orden if m in por_moneda] + [
        m for m in por_moneda if m not in orden
    ]

    alto = src.row_dimensions[data_style].height
    alto_sub = src.row_dimensions[subtotal_style].height
    dst_r = 1
    for moneda in monedas:
        etiqueta = _MONEDA_ETIQUETA.get(moneda, moneda or "SIN MONEDA")
        # Banda de título de la moneda (estilo de fila TOTAL).
        _copiar_fila_desplazada(src, dst, subtotal_style, dst_r, ncols)
        dst.cell(dst_r, 1).value = f"AGENTES DE ADUANAS {etiqueta}"
        dst.cell(dst_r, 15).value = None
        dst.merge_cells(start_row=dst_r, start_column=1, end_row=dst_r, end_column=ncols_dst)
        dst_r += 1
        # Cabecera. Se añade el encabezado 'N° Registro' en la columna S (19),
        # que la plantilla de esta hoja no traía (estilo de la cabecera vecina).
        _copiar_fila_desplazada(src, dst, header_row, dst_r, ncols, es_cabecera=True)
        _clonar_estilo(dst.cell(dst_r, 19), dst.cell(dst_r, 18))
        dst.cell(dst_r, 19).value = "N° Registro"
        if src.row_dimensions[header_row].height:
            dst.row_dimensions[dst_r].height = src.row_dimensions[header_row].height
        dst_r += 1
        # Grupos por O/C (ordenados).
        subtotales: list[int] = []
        for oc in sorted(por_moneda[moneda]):
            filas = por_moneda[moneda][oc]
            nombre = nombre_por_oc.get(oc, "")
            data_ini = dst_r
            for i, f in enumerate(filas):
                _escribir_fila_agente(
                    src, data_style, dst, dst_r, f, ncols, sp_cfg,
                    nombre if i == 0 else None, ret_cfg,
                )
                if alto:
                    dst.row_dimensions[dst_r].height = alto
                dst_r += 1
            data_fin = dst_r - 1
            _copiar_fila_desplazada(src, dst, subtotal_style, dst_r, ncols)
            if alto_sub:
                dst.row_dimensions[dst_r].height = alto_sub
            dst.cell(dst_r, 1).value = (f"TOTAL {oc}").strip()
            dst.cell(dst_r, 15).value = f"=SUM(O{data_ini}:O{data_fin})"
            dst.merge_cells(start_row=dst_r, start_column=1, end_row=dst_r, end_column=14)
            subtotales.append(dst_r)
            ref["oc"][(oc, moneda)] = dst_r
            dst_r += 1
        # Total de la moneda.
        _copiar_fila_desplazada(src, dst, subtotal_style, dst_r, ncols)
        if alto_sub:
            dst.row_dimensions[dst_r].height = alto_sub
        dst.cell(dst_r, 1).value = f"TOTAL {etiqueta}"
        dst.cell(dst_r, 15).value = (
            "=" + "+".join(f"O{r}" for r in subtotales) if subtotales else 0
        )
        dst.merge_cells(start_row=dst_r, start_column=1, end_row=dst_r, end_column=14)
        ref["moneda"][moneda] = dst_r
        dst_r += 2  # línea en blanco de separación entre monedas

    _ajustar_anchos_agentes(dst, dst_r)

    pos_idx = wb.sheetnames.index("Detalle de agentes")
    del wb["Detalle de agentes"]
    dst.title = "Detalle de agentes"
    wb.move_sheet(
        "Detalle de agentes",
        offset=pos_idx - wb.sheetnames.index("Detalle de agentes"),
    )
    return ref


def construir_detalle(
    data: dict,
    fecha_inicio: str | None,
    fecha_final: str | None,
    output_path: Path,
    sharepoint_cfg: dict | None = None,
    agente_rucs: list[str] | None = None,
    relacionados_rucs: list[str] | None = None,
    retencion_cfg: dict | None = None,
    tipo_cambio: float | None = None,
    pos_sin_ret: set | None = None,
) -> Path:
    wb = openpyxl.load_workbook(_PLANTILLA)

    tc = float(tipo_cambio) if tipo_cambio else TIPO_CAMBIO_DEFAULT
    # El mismo tipo de cambio va al Resumen (celda del TOTAL CONSOLIDADO).
    if "Resumen" in wb.sheetnames:
        wb["Resumen"][_CELDA_TIPO_CAMBIO] = tc

    # Operaciones que NO aplican retención (p. ej. Pagos servicios). Se prefiere
    # el set recibido (config actual); si no, se deriva del snapshot del proceso.
    if pos_sin_ret is None:
        pos_sin_ret = {
            o["pos"]
            for o in data.get("operaciones", [])
            if not o.get("aplica_retencion", True)
        }
    # Config de retención: interruptor + RUCs exceptuados + tipo de cambio.
    ret_cfg = {
        "activo": bool((retencion_cfg or {}).get("activo")),
        "rucs": {
            _norm_ruc(r)
            for r in ((retencion_cfg or {}).get("rucs") or [])
            if str(r).strip()
        },
        "tipo_cambio": tc,
        "pos_sin_ret": pos_sin_ret,
    }

    # Agrupar por O/C las facturas que incluyen a un agente o proveedor
    # relacionado. Esas filas salen de su Operación normal (van solo a 'Agentes
    # de Aduanas').
    ocs_consolidadas, nombre_por_oc, ruc_por_oc, grupos_agentes = _agrupar_agentes(
        data["filas"], agente_rucs or [], relacionados_rucs or []
    )

    grupos: dict = {}
    for f in data["filas"]:
        if _es_fila_agente(f, ocs_consolidadas):
            continue  # va a 'Agentes de Aduanas' (O/C consolidada o TIPO 21)
        pos = f.get("__pos")
        if pos is None:  # "Otros" no va al Excel
            continue
        grupos.setdefault(pos, []).append(f)

    operaciones = data.get("operaciones", [])
    # Primero 'Detalle de agentes' (para conocer las filas de sus totales) y
    # luego 'Detalle', que enlaza sus resúmenes con fórmulas a esa hoja.
    ref_agentes = _construir_detalle_agentes_sheet(
        wb, grupos_agentes, nombre_por_oc, sharepoint_cfg, ret_cfg
    )
    total_rows = _construir_detalle_sheet(
        wb, grupos, operaciones, fecha_inicio, fecha_final, sharepoint_cfg,
        grupos_agentes, nombre_por_oc, ruc_por_oc, ref_agentes, ret_cfg,
    )
    _rellenar_resumen(wb, total_rows, operaciones)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path
