"""Genera el Excel de descarga rellenando la plantilla del usuario
(app/resources/plantilla.xlsx), conservando exactamente sus colores, layout,
secciones fijas (Agentes de Aduanas, Pagos al Personal, Seguros) y fórmulas.

Solo se inyectan los datos en las secciones 'Operación N' (por posición), y en
el Resumen se rellenan los importes de 'I. PAGOS A REALIZAR'. La categoría
'Otros' (sin categoría) NO se incluye.

Columnas calculadas (supuestos, confirmar):
- % DET = columna DETRACCION (tasa).  DET = IMPORTE * % DET / 100.  Neto = SALDO - DET.
"""

import re
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.formula.translate import Translator
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services import sharepoint

# Columna SUSTENTO / LINK FACTURA (donde va el hipervínculo al PDF).
_COL_LINK = 19
_LINK_FONT = Font(color="0563C1", underline="single")

# Columna DET (12): formato contable con 2 decimales (cero -> guion).
_COL_DET = 12
_DET_FMT = "_-* #,##0.00_-;\\-* #,##0.00_-;_-* \\-??_-;_-@_-"

_PLANTILLA = Path(__file__).resolve().parent.parent / "resources" / "plantilla.xlsx"
_DATETIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}:\d{2}")
_OPERACION_RE = re.compile(r"^\s*Operaci.n\s+(\d+)", re.IGNORECASE)

# Detalle: columna (1-based) -> clave de texto en los datos.
_TXT = {
    1: "PROVEEDOR", 2: "TIPO", 3: "NUMERO",
    4: "FEC REGISTRO", 5: "FECHA DOC.", 6: "FEC. VCTO",
    16: "PRODUCTO", 17: "ORD_COMPRA", 18: "REGISTRO", 19: "REGISTRO",
}
_FECHA_COLS = {4, 5, 6}


def _num(value) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0


def _fecha(value) -> str:
    s = "" if value is None else str(value).strip()
    m = _DATETIME_RE.match(s)
    return m.group(1) if m else s


def _valores_fila(f: dict) -> dict:
    """Valores por columna (1-based) para una fila del Detalle."""
    importe = round(_num(f.get("IMPORTE")), 2)
    pagado = round(_num(f.get("PAGADO")), 2)
    saldo = round(_num(f.get("SALDO")), 2)
    p_det = _num(f.get("DETRACCION"))
    det = round(importe * p_det / 100, 2)
    vals = {i: (_fecha(f.get(k)) if i in _FECHA_COLS else f.get(k, "")) for i, k in _TXT.items()}
    # %DET va en una celda con formato de porcentaje: guardar como fracción
    # (12 -> 0.12) para que Excel muestre "12 %", no "1200 %".
    # RET y Neto se escriben como fórmulas de Excel (ver _construir_detalle_sheet).
    vals.update({7: importe, 8: pagado, 9: saldo, 11: p_det / 100, 12: det})
    return vals


def _norm_ruc(ruc) -> str:
    return re.sub(r"\.0$", "", str(ruc).strip())


def _neto(f: dict) -> float:
    """Neto numérico de una fila, replicando la fórmula del Detalle (RET=0, pues
    el %RET no viene en los datos):
      si DET>0 y |PAGADO-DET|<1  -> SALDO
      si DET>0 y PAGADO=0        -> SALDO-DET
      en otro caso               -> SALDO
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
    return round(base, 2)


def _agrupar_agentes(filas: list[dict], agente_rucs: list[str]) -> tuple:
    """Detecta las O/C que incluyen a un agente aduanero y agrupa sus facturas.

    Devuelve:
      - ocs_agente: set de N° O/C-O/S que tienen un agente.
      - nombre_por_oc: O/C -> nombre del proveedor-agente (para depositar).
      - grupos: (O/C, MONEDA) -> lista de filas de esa orden y moneda.
    """
    rucs = {_norm_ruc(r) for r in (agente_rucs or []) if str(r).strip()}
    if not rucs:
        return set(), {}, {}

    nombre_por_oc: dict[str, str] = {}
    for f in filas:
        oc = str(f.get("ORD_COMPRA", "")).strip()
        if oc and _norm_ruc(f.get("RUC", "")) in rucs and oc not in nombre_por_oc:
            nombre_por_oc[oc] = str(f.get("PROVEEDOR", "")).strip()

    ocs_agente = set(nombre_por_oc)
    grupos: dict = {}
    for f in filas:
        oc = str(f.get("ORD_COMPRA", "")).strip()
        if oc and oc in ocs_agente:
            moneda = str(f.get("MONEDA", "")).strip().upper()
            grupos.setdefault((oc, moneda), []).append(f)
    return ocs_agente, nombre_por_oc, grupos


def _copiar_celda(s, d, src_r: int, dst_r: int, col: int) -> None:
    """Copia estilo y valor de s->d, trasladando fórmulas al desplazamiento de fila."""
    if s.has_style:
        d._style = copy(s._style)
    v = s.value
    if isinstance(v, str) and v.startswith("=") and src_r != dst_r:
        try:
            v = Translator(v, origin=f"{get_column_letter(col)}{src_r}").translate_formula(
                f"{get_column_letter(col)}{dst_r}"
            )
        except Exception:
            pass  # #REF! u otras fórmulas no trasladables: dejar tal cual
    d.value = v


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


def _escribir_resumen_agente(src, estilo_row, dst, r, nombre, oc, total, ncols):
    """Escribe una fila resumen en la sección Agentes: nombre del agente, O/C y
    el total (Neto) a depositar. Toma el estilo de la fila modelo."""
    for c in range(1, ncols + 1):
        s = src.cell(estilo_row, c)
        d = dst.cell(r, c)
        if s.has_style:
            d._style = copy(s._style)
        d.value = None
    dst.cell(r, 1).value = nombre     # PROVEEDOR
    dst.cell(r, 15).value = total     # Neto (columna O)
    dst.cell(r, 16).value = nombre    # AGENTE ADUANERO
    dst.cell(r, 17).value = oc        # N° O/C-O/S


def _escribir_fila(src, estilo_row, dst, r, fila, ncols, sp_cfg) -> None:
    """Escribe una fila de datos en `r`, con el estilo de `estilo_row`."""
    vals = _valores_fila(fila)
    for c in range(1, ncols + 1):
        s = src.cell(estilo_row, c)
        d = dst.cell(r, c)
        if s.has_style:
            d._style = copy(s._style)
        d.value = vals.get(c)
    # DET con dos decimales.
    dst.cell(r, _COL_DET).number_format = _DET_FMT
    # %RET como porcentaje (mismo formato que %DET); RET = %RET * IMPORTE.
    dst.cell(r, 13).number_format = dst.cell(r, 11).number_format
    dst.cell(r, 14).value = f"=M{r}*G{r}"
    # Neto (fórmula viva):
    #   si DET>0 y |PAGADO-DET|<1  -> SALDO
    #   si DET>0 y PAGADO=0        -> SALDO-DET
    #   en otro caso               -> SALDO   ; luego - RET
    dst.cell(r, 15).value = (
        f"=IF(AND(L{r}>0,ABS(H{r}-L{r})<1),I{r},"
        f"IF(AND(L{r}>0,H{r}=0),I{r}-L{r},I{r}))-N{r}"
    )
    # Hipervínculo al PDF en SUSTENTO (nombre del PDF = registro), en la carpeta
    # del mes que le toca. Si no hay carpeta para ese mes, queda en blanco.
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


def _construir_detalle_sheet(
    wb, grupos, operaciones, fecha_inicio, fecha_final, sp_cfg,
    grupos_agentes=None, nombre_por_oc=None,
) -> dict:
    src = wb["Detalle"]
    # max_column reporta 16384 por celdas con formato vacío; las columnas
    # reales del Detalle llegan hasta S (SUSTENTO / LINK FACTURA) = 19.
    ncols = 19
    ops = _detectar_operaciones(src)
    agentes = _detectar_agentes(src)
    grupos_agentes = grupos_agentes or {}
    nombre_por_oc = nombre_por_oc or {}
    # Texto actual de cada operación (config de la app manda sobre la plantilla).
    op_texto = {o["pos"]: o.get("texto", "") for o in operaciones}

    dst = wb.create_sheet("__detalle_tmp__")
    for letra, dim in src.column_dimensions.items():
        if dim.width:
            dst.column_dimensions[letra].width = dim.width

    row_map: dict = {}
    total_rows: dict = {}   # pos -> fila TOTAL (destino) de esa operación
    total_merges: list = []
    dst_r = 1
    src_r = 1
    while src_r <= src.max_row:
        if src_r in ops:
            pos, total_row = ops[src_r]
            filas = grupos.get(pos, [])
            estilo_row = src_r  # fila de datos modelo (estilos)
            data_ini = dst_r
            if filas:
                alto = src.row_dimensions[estilo_row].height
                for f in filas:
                    _escribir_fila(src, estilo_row, dst, dst_r, f, ncols, sp_cfg)
                    if alto:
                        dst.row_dimensions[dst_r].height = alto
                    dst_r += 1
            else:
                # Sin datos: conservar las filas en blanco de la plantilla.
                for rr in range(src_r, total_row):
                    for c in range(1, ncols + 1):
                        _copiar_celda(src.cell(rr, c), dst.cell(dst_r, c), rr, dst_r, c)
                    if src.row_dimensions[rr].height:
                        dst.row_dimensions[dst_r].height = src.row_dimensions[rr].height
                    dst_r += 1
            data_fin = dst_r - 1
            # Fila TOTAL (estilo de la plantilla) con Neto sumado del rango real.
            for c in range(1, ncols + 1):
                _copiar_celda(src.cell(total_row, c), dst.cell(dst_r, c), total_row, dst_r, c)
            if src.row_dimensions[total_row].height:
                dst.row_dimensions[dst_r].height = src.row_dimensions[total_row].height
            dst.cell(dst_r, 15).value = f"=SUM(O{data_ini}:O{data_fin})"
            total_merges.append(dst_r)
            total_rows[pos] = dst_r
            dst_r += 1
            src_r = total_row + 1
        elif src_r in agentes:
            # Sección 'AGENTES DE ADUANAS SOL/DOL': una fila resumen por O/C
            # (agente, N° O/C-O/S y total a depositar) de esa moneda.
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
                    nombre = nombre_por_oc.get(oc, "")
                    total = round(sum(_neto(f) for f in filas), 2)
                    _escribir_resumen_agente(
                        src, estilo_row, dst, dst_r, nombre, oc, total, ncols
                    )
                    if alto:
                        dst.row_dimensions[dst_r].height = alto
                    dst_r += 1
            else:
                for rr in range(src_r, total_row):
                    for c in range(1, ncols + 1):
                        _copiar_celda(src.cell(rr, c), dst.cell(dst_r, c), rr, dst_r, c)
                    if src.row_dimensions[rr].height:
                        dst.row_dimensions[dst_r].height = src.row_dimensions[rr].height
                    dst_r += 1
            data_fin = dst_r - 1
            for c in range(1, ncols + 1):
                _copiar_celda(src.cell(total_row, c), dst.cell(dst_r, c), total_row, dst_r, c)
            if src.row_dimensions[total_row].height:
                dst.row_dimensions[dst_r].height = src.row_dimensions[total_row].height
            if resumen:
                dst.cell(dst_r, 15).value = f"=SUM(O{data_ini}:O{data_fin})"
            total_merges.append(dst_r)
            dst_r += 1
            src_r = total_row + 1
        else:
            for c in range(1, ncols + 1):
                _copiar_celda(src.cell(src_r, c), dst.cell(dst_r, c), src_r, dst_r, c)
            if src.row_dimensions[src_r].height:
                dst.row_dimensions[dst_r].height = src.row_dimensions[src_r].height
            # Si es un título "Operación N", re-rotularlo con el texto actual de
            # la configuración (la plantilla puede tener nombres desactualizados).
            a = src.cell(src_r, 1).value
            m = _OPERACION_RE.match(str(a)) if a else None
            if m:
                pos = int(m.group(1))
                texto = (op_texto.get(pos) or "").strip()
                dst.cell(dst_r, 1).value = (
                    f"Operación {pos}" + (f" - {texto}" if texto else "")
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
            filas = grupos[pos]
            dst_r += 1  # fila en blanco de separación
            # Título.
            for c in range(1, ncols + 1):
                _copiar_celda(src.cell(m_titulo, c), dst.cell(dst_r, c), m_titulo, dst_r, c)
            texto = (op_texto.get(pos) or "").strip()
            dst.cell(dst_r, 1).value = f"Operación {pos}" + (f" - {texto}" if texto else "")
            dst_r += 1
            # Cabecera.
            for c in range(1, ncols + 1):
                _copiar_celda(src.cell(m_header, c), dst.cell(dst_r, c), m_header, dst_r, c)
            dst_r += 1
            # Datos.
            data_ini = dst_r
            alto = src.row_dimensions[m_data].height
            for f in filas:
                _escribir_fila(src, m_data, dst, dst_r, f, ncols, sp_cfg)
                if alto:
                    dst.row_dimensions[dst_r].height = alto
                dst_r += 1
            data_fin = dst_r - 1
            # TOTAL.
            for c in range(1, ncols + 1):
                _copiar_celda(src.cell(m_total, c), dst.cell(dst_r, c), m_total, dst_r, c)
            if src.row_dimensions[m_total].height:
                dst.row_dimensions[dst_r].height = src.row_dimensions[m_total].height
            dst.cell(dst_r, 15).value = f"=SUM(O{data_ini}:O{data_fin})"
            dst.merge_cells(start_row=dst_r, start_column=1, end_row=dst_r, end_column=14)
            total_rows[pos] = dst_r
            dst_r += 1

    # Merges verbatim (de filas copiadas tal cual).
    for mc in list(src.merged_cells.ranges):
        if mc.min_row in row_map and mc.max_row in row_map:
            dst.merge_cells(
                start_row=row_map[mc.min_row], start_column=mc.min_col,
                end_row=row_map[mc.max_row], end_column=mc.max_col,
            )
    # Merges de las filas TOTAL de las secciones Operación (A:N).
    for tr in total_merges:
        dst.merge_cells(start_row=tr, start_column=1, end_row=tr, end_column=14)

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


def _rellenar_resumen(wb, total_rows: dict, operaciones: list) -> None:
    if "Resumen" not in wb.sheetnames:
        return
    ws = wb["Resumen"]
    op_texto = {o["pos"]: o.get("texto", "") for o in operaciones}
    # En 'I. PAGOS A REALIZAR' cada fila tiene la etiqueta 'Operación N' en col B
    # y una fórmula en col D que apunta al TOTAL de esa operación en Detalle.
    # Re-rotulamos la etiqueta con el nombre actual (la plantilla puede tenerlo
    # desactualizado) y re-apuntamos la fórmula a la nueva fila TOTAL.
    for r in range(1, ws.max_row + 1):
        b = ws.cell(r, 2).value
        m = _OPERACION_RE.match(str(b)) if b else None
        if m:
            pos = int(m.group(1))
            texto = (op_texto.get(pos) or "").strip()
            ws.cell(r, 2).value = (
                f"Operación {pos}" + (f" - {texto}" if texto else "")
            )
            if pos in total_rows:
                ws.cell(r, 4).value = f"=+Detalle!O{total_rows[pos]}"


# Hoja 'Detalle de agentes': columna (1-based) -> clave de texto (layout propio,
# SIN la columna PLAZO del Detalle: %DET=10, DET=11, %RET=12, RET=13, Neto=14).
_TXT_AG = {
    1: "PROVEEDOR", 2: "TIPO", 3: "NUMERO",
    4: "FEC REGISTRO", 5: "FECHA DOC.", 6: "FEC. VCTO",
    15: "PRODUCTO", 17: "ORD_COMPRA", 19: "REGISTRO",
}


def _valores_fila_ag(f: dict) -> dict:
    """Valores por columna para una fila de la hoja 'Detalle de agentes'."""
    importe = round(_num(f.get("IMPORTE")), 2)
    pagado = round(_num(f.get("PAGADO")), 2)
    saldo = round(_num(f.get("SALDO")), 2)
    p_det = _num(f.get("DETRACCION"))
    det = round(importe * p_det / 100, 2)
    vals = {
        i: (_fecha(f.get(k)) if i in _FECHA_COLS else f.get(k, ""))
        for i, k in _TXT_AG.items()
    }
    vals.update({7: importe, 8: pagado, 9: saldo, 10: p_det / 100, 11: det})
    return vals


def _escribir_fila_agente(src, estilo_row, dst, r, f, ncols, sp_cfg, agente):
    """Escribe una factura en la hoja 'Detalle de agentes'."""
    vals = _valores_fila_ag(f)
    for c in range(1, ncols + 1):
        s = src.cell(estilo_row, c)
        d = dst.cell(r, c)
        if s.has_style:
            d._style = copy(s._style)
        d.value = vals.get(c)
    dst.cell(r, 11).number_format = _DET_FMT                       # DET
    dst.cell(r, 12).number_format = dst.cell(r, 10).number_format  # %RET como %DET
    dst.cell(r, 13).value = f"=L{r}*G{r}"                          # RET = %RET*IMPORTE
    dst.cell(r, 14).value = f"=I{r}-K{r}-M{r}"                     # Neto = SALDO-DET-RET
    if agente:
        dst.cell(r, 16).value = agente                            # AGENTE ADUANERO
    registro = str(f.get("REGISTRO") or "").strip()
    if sp_cfg and registro:
        url = sharepoint.link_factura(
            sp_cfg.get("link_principal"), sp_cfg.get("meses"), registro
        )
        if url:
            cel = dst.cell(r, _COL_LINK)
            cel.hyperlink = url
            cel.font = _LINK_FONT


def _construir_detalle_agentes_sheet(wb, grupos_agentes, nombre_por_oc, sp_cfg):
    """Reconstruye la hoja 'Detalle de agentes' con el detalle de todas las
    facturas agrupadas por O/C, con un subtotal por grupo y un total general."""
    if "Detalle de agentes" not in wb.sheetnames:
        return
    src = wb["Detalle de agentes"]
    ncols = 19
    header_row, data_style, subtotal_style = 2, 3, 6

    dst = wb.create_sheet("__agentes_tmp__")
    for letra, dim in src.column_dimensions.items():
        if dim.width:
            dst.column_dimensions[letra].width = dim.width

    # Cabecera (fila 2 de la plantilla), dejando la fila 1 en blanco.
    dst_r = 2
    for c in range(1, ncols + 1):
        _copiar_celda(src.cell(header_row, c), dst.cell(dst_r, c), header_row, dst_r, c)
    if src.row_dimensions[header_row].height:
        dst.row_dimensions[dst_r].height = src.row_dimensions[header_row].height
    dst_r += 1

    alto = src.row_dimensions[data_style].height
    subtotales: list[int] = []
    for (oc, _moneda), filas in sorted(grupos_agentes.items()):
        nombre = nombre_por_oc.get(oc, "")
        data_ini = dst_r
        for i, f in enumerate(filas):
            _escribir_fila_agente(
                src, data_style, dst, dst_r, f, ncols, sp_cfg,
                nombre if i == 0 else None,
            )
            if alto:
                dst.row_dimensions[dst_r].height = alto
            dst_r += 1
        data_fin = dst_r - 1
        # Subtotal del grupo (estilo de la fila TOTAL de la plantilla).
        for c in range(1, ncols + 1):
            _copiar_celda(src.cell(subtotal_style, c), dst.cell(dst_r, c), subtotal_style, dst_r, c)
        if src.row_dimensions[subtotal_style].height:
            dst.row_dimensions[dst_r].height = src.row_dimensions[subtotal_style].height
        dst.cell(dst_r, 1).value = f"TOTAL {oc}"
        dst.cell(dst_r, 14).value = f"=SUM(N{data_ini}:N{data_fin})"
        dst.merge_cells(start_row=dst_r, start_column=1, end_row=dst_r, end_column=13)
        subtotales.append(dst_r)
        dst_r += 1

    if subtotales:
        for c in range(1, ncols + 1):
            _copiar_celda(src.cell(subtotal_style, c), dst.cell(dst_r, c), subtotal_style, dst_r, c)
        dst.cell(dst_r, 1).value = "TOTAL GENERAL"
        dst.cell(dst_r, 14).value = "=" + "+".join(f"N{r}" for r in subtotales)
        dst.merge_cells(start_row=dst_r, start_column=1, end_row=dst_r, end_column=13)

    pos_idx = wb.sheetnames.index("Detalle de agentes")
    del wb["Detalle de agentes"]
    dst.title = "Detalle de agentes"
    wb.move_sheet(
        "Detalle de agentes",
        offset=pos_idx - wb.sheetnames.index("Detalle de agentes"),
    )


def construir_detalle(
    data: dict,
    fecha_inicio: str | None,
    fecha_final: str | None,
    output_path: Path,
    sharepoint_cfg: dict | None = None,
    agente_rucs: list[str] | None = None,
) -> Path:
    wb = openpyxl.load_workbook(_PLANTILLA)

    # Agrupar por O/C las facturas que incluyen a un agente aduanero. Esas filas
    # salen de su Operación normal (van solo a 'Agentes de Aduanas').
    ocs_agente, nombre_por_oc, grupos_agentes = _agrupar_agentes(
        data["filas"], agente_rucs or []
    )

    grupos: dict = {}
    for f in data["filas"]:
        oc = str(f.get("ORD_COMPRA", "")).strip()
        if oc and oc in ocs_agente:
            continue  # consolidada en Agentes de Aduanas
        pos = f.get("__pos")
        if pos is None:  # "Otros" no va al Excel
            continue
        grupos.setdefault(pos, []).append(f)

    operaciones = data.get("operaciones", [])
    total_rows = _construir_detalle_sheet(
        wb, grupos, operaciones, fecha_inicio, fecha_final, sharepoint_cfg,
        grupos_agentes, nombre_por_oc,
    )
    _rellenar_resumen(wb, total_rows, operaciones)
    _construir_detalle_agentes_sheet(wb, grupos_agentes, nombre_por_oc, sharepoint_cfg)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path
