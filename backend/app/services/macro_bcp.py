"""Macros de pago masivo a proveedores del BCP (una por moneda).

A partir de las facturas de 'Pago masivo proveedores' se arma un abono por
proveedor (fila 'A', con su cuenta y el total) seguido de sus facturas (filas
'D'), y se escribe en la plantilla .xlsm del banco.

La plantilla se edita directamente en su XML y solo en las celdas que cambian
(fila 7 y las filas de abonos). No se usa openpyxl para guardarla porque
descarta los botones (controles de formulario) desde los que se ejecuta la
macro del banco. Todo lo demás del archivo queda idéntico.
"""

import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import date
from xml.sax.saxutils import escape, unescape

import openpyxl

from app.services.excel_utils import ProcesamientoError

HOJA_INPUT = "Archivo Excel Proveedores Input"
FILA_CARGO = 7          # cantidad de abonos, fecha de proceso y monto total
FILA_DATOS = 11         # primera fila de abonos
# La sección 'DATOS DEL ABONO CON CHEQUE DE GERENCIA' marca el final del espacio
# para abonos a cuenta: de ahí para abajo no se toca.
_MARCA_FIN = "CHEQUE"
COLUMNAS = "ABCDEFGHIJKLMNO"
CODIGO_MONEDA = {"SOL": "S", "USD": "D"}
_TIPO_DOC_PAGAR = "F "   # factura (con el espacio que pide el formato)
_CORRELATIVO = "   "
_VALIDAR_IDC = "S"


def _norm_ruc(ruc) -> str:
    return re.sub(r"\.0$", "", str(ruc or "").strip())


def _texto(v) -> str:
    """Valor de celda como texto (un número entero sin '.0')."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _sin_tildes(s) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().upper()


def _monto(v: float) -> str:
    return f"{round(v, 2):.2f}"


def numero_documento(numero) -> str:
    """Lo que va tras el último guion, sin ceros a la izquierda:
    'F002-00012369' -> '12369'. Si no es numérico se deja tal cual."""
    s = str(numero or "").strip().split("-")[-1].strip()
    return (s.lstrip("0") or "0") if s.isdigit() else s


# ---- Base de cuentas ---------------------------------------------------------

def leer_base_cuentas(contenido: bytes) -> dict[str, dict]:
    """RUC -> datos de su cuenta, desde la primera hoja de la base (mismas
    columnas A-G que la macro: tipo de registro, tipo de cuenta, cuenta, tipo
    de documento, N° de documento, correlativo y nombre)."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    except Exception as exc:
        raise ProcesamientoError("No se pudo leer la base de cuentas (¿es un .xlsx?).") from exc
    ws = wb.worksheets[0]
    filas = ws.iter_rows(min_col=1, max_col=7, values_only=True)
    cabecera = [_sin_tildes(v) for v in next(filas, ())]
    if len(cabecera) < 7 or "CUENTA" not in cabecera[2] or "DOCUMENTO" not in cabecera[4]:
        raise ProcesamientoError(
            "La base de cuentas no tiene el formato esperado: la columna C debe ser "
            "la cuenta de abono y la E el número de documento (RUC)."
        )
    cuentas: dict[str, dict] = {}
    for fila in filas:
        fila = tuple(fila) + (None,) * (7 - len(fila))
        ruc = _norm_ruc(fila[4])
        if not ruc:
            continue
        cuentas[ruc] = {
            "tipo_cuenta": _texto(fila[1]),
            "cuenta": _texto(fila[2]),
            "tipo_doc": _texto(fila[3]) or "6",
            "nombre": _texto(fila[6]),
        }
    wb.close()
    return cuentas


# ---- Abonos ------------------------------------------------------------------

@dataclass
class Documento:
    numero: str
    monto: float


@dataclass
class Abono:
    ruc: str
    nombre: str
    tipo_cuenta: str
    cuenta: str
    tipo_doc: str
    en_bd: bool
    documentos: list[Documento] = field(default_factory=list)

    @property
    def total(self) -> float:
        # Cada factura ya va redondeada a 2 decimales; luego se suman.
        return round(sum(d.monto for d in self.documentos), 2)


def armar_abonos(facturas: list[tuple[dict, float]], cuentas: dict[str, dict]) -> list[Abono]:
    """Un abono por RUC, en el orden en que aparece cada proveedor. `facturas`
    son (fila del proceso, neto). El nombre y la cuenta salen de la base; si el
    RUC no está, va con el nombre del informe y la cuenta en blanco, para
    completarla a mano en la macro."""
    por_ruc: dict[str, Abono] = {}
    for fila, neto in facturas:
        ruc = _norm_ruc(fila.get("RUC"))
        abono = por_ruc.get(ruc)
        if abono is None:
            cta = cuentas.get(ruc)
            abono = Abono(
                ruc=ruc,
                nombre=(cta or {}).get("nombre") or str(fila.get("PROVEEDOR") or "").strip(),
                tipo_cuenta=(cta or {}).get("tipo_cuenta", ""),
                cuenta=(cta or {}).get("cuenta", ""),
                tipo_doc=(cta or {}).get("tipo_doc") or "6",
                en_bd=cta is not None,
            )
            por_ruc[ruc] = abono
        abono.documentos.append(Documento(numero_documento(fila.get("NUMERO")), round(neto, 2)))
    return list(por_ruc.values())


def _filas_macro(abonos: list[Abono], moneda: str) -> list[tuple[str, dict]]:
    """('A' | 'D', columna -> valor) para cada fila de la macro."""
    codigo = CODIGO_MONEDA.get(moneda, moneda)
    filas: list[tuple[str, dict]] = []
    for ab in abonos:
        filas.append(("A", {
            "A": "A", "B": ab.tipo_cuenta, "C": ab.cuenta, "D": ab.tipo_doc,
            "E": f"{ab.ruc} " if ab.ruc else "", "F": _CORRELATIVO, "G": ab.nombre,
            "H": codigo, "I": _monto(ab.total), "J": _VALIDAR_IDC,
            "K": f"{len(ab.documentos):04d}",
        }))
        for doc in ab.documentos:
            filas.append(("D", {
                "A": "D", "L": _TIPO_DOC_PAGAR, "M": doc.numero, "N": codigo,
                "O": _monto(doc.monto),
            }))
    return filas


# ---- XML de la plantilla -----------------------------------------------------

_FILA_RE = re.compile(r'<row\b[^>]*?\br="(\d+)"[^>]*?(?:/>|>.*?</row>)', re.S)
_CELDA_RE = re.compile(r'<c\b([^>]*?)(?:/>|>(.*?)</c>)', re.S)
_REF_RE = re.compile(r'\br="([A-Z]+)(\d+)"')


def _ruta_hoja(z: zipfile.ZipFile, nombre: str) -> str:
    """Ruta dentro del .xlsm del XML de la hoja `nombre`."""
    wb = z.read("xl/workbook.xml").decode("utf-8")
    tag = next(
        (m.group(0) for m in re.finditer(r"<sheet\b[^>]*>", wb)
         if re.search(r'\bname="%s"' % re.escape(escape(nombre, {'"': "&quot;"})), m.group(0))),
        None,
    )
    if tag is None:
        raise ProcesamientoError(f"La plantilla no tiene la hoja «{nombre}».")
    rid = re.search(r'\br:id="([^"]+)"', tag).group(1)
    rels = z.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    rel = next(m.group(0) for m in re.finditer(r"<Relationship\b[^>]*>", rels)
               if re.search(r'\bId="%s"' % re.escape(rid), m.group(0)))
    destino = re.search(r'\bTarget="([^"]+)"', rel).group(1)
    return destino.lstrip("/") if destino.startswith("/") else f"xl/{destino}"


def _textos_compartidos(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    x = z.read("xl/sharedStrings.xml").decode("utf-8")
    return [
        unescape("".join(re.findall(r"<t\b[^>]*>(.*?)</t>", si, re.S)))
        for si in re.findall(r"<si\b[^>]*>(.*?)</si>", x, re.S)
    ]


def _celdas(fila_xml: str) -> dict[str, tuple[str, str | None, str]]:
    """columna -> (atributos, contenido, xml completo) de cada celda de la fila."""
    out = {}
    for m in _CELDA_RE.finditer(fila_xml):
        ref = _REF_RE.search(m.group(1))
        if ref:
            out[ref.group(1)] = (m.group(1), m.group(2), m.group(0))
    return out


def _valor(attrs: str, contenido: str | None, compartidos: list[str]) -> str:
    if not contenido:
        return ""
    tipo = re.search(r'\bt="([^"]+)"', attrs)
    tipo = tipo.group(1) if tipo else ""
    if tipo == "inlineStr":
        return unescape("".join(re.findall(r"<t\b[^>]*>(.*?)</t>", contenido, re.S)))
    v = re.search(r"<v>(.*?)</v>", contenido, re.S)
    if not v:
        return ""
    if tipo == "s":
        i = int(v.group(1))
        return compartidos[i] if i < len(compartidos) else ""
    return unescape(v.group(1))


def _estilo(attrs: str) -> str | None:
    m = re.search(r'\bs="(\d+)"', attrs)
    return m.group(1) if m else None


def _atributos_fila(fila_xml: str) -> str:
    """Atributos de <row> (alto, spans...) sin el número de fila."""
    apertura = re.match(r"<row\b([^>]*?)/?>", fila_xml).group(1)
    return re.sub(r'\s*\br="\d+"', "", apertura)


def _celda(col: str, r: int, estilo: str | None, valor) -> str:
    s = f' s="{estilo}"' if estilo else ""
    if valor in (None, ""):
        return f'<c r="{col}{r}"{s}/>'
    texto = escape(str(valor))
    return f'<c r="{col}{r}"{s} t="inlineStr"><is><t xml:space="preserve">{texto}</t></is></c>'


def _col_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    return n


def _poner_celdas(fila_xml: str, r: int, valores: dict[str, str]) -> str:
    """Reescribe (o agrega, en su orden) las celdas `valores` de una fila,
    conservando su estilo y el resto de la fila tal cual."""
    celdas = {col: xml for col, (_a, _c, xml) in _celdas(fila_xml).items()}
    for col, valor in valores.items():
        previo = _celdas(fila_xml).get(col)
        celdas[col] = _celda(col, r, _estilo(previo[0]) if previo else None, valor)
    cuerpo = "".join(celdas[c] for c in sorted(celdas, key=_col_num))
    return f'<row r="{r}"{_atributos_fila(fila_xml)}>{cuerpo}</row>'


def _vaciar(fila_xml: str) -> str:
    """La misma fila, con el formato pero sin valores."""
    def sin_valor(m: re.Match) -> str:
        return "<c%s/>" % re.sub(r'\s+t="[^"]*"', "", m.group(1)).rstrip("/")
    return _CELDA_RE.sub(sin_valor, fila_xml)


@dataclass
class _Plantilla:
    ruta: str
    xml: str
    filas: dict[int, str]
    fin: int                 # fila de la sección de cheques (no se toca)


def _abrir_plantilla(contenido: bytes) -> _Plantilla:
    try:
        z = zipfile.ZipFile(io.BytesIO(contenido))
    except zipfile.BadZipFile as exc:
        raise ProcesamientoError("La plantilla no es un archivo de Excel válido.") from exc
    with z:
        if "xl/vbaProject.bin" not in z.namelist():
            raise ProcesamientoError("La plantilla no trae la macro: súbela como .xlsm.")
        ruta = _ruta_hoja(z, HOJA_INPUT)
        xml = z.read(ruta).decode("utf-8")
        compartidos = _textos_compartidos(z)
    filas = {int(m.group(1)): m.group(0) for m in _FILA_RE.finditer(xml)}
    fin = next(
        (r for r in sorted(filas) if r > FILA_DATOS
         and _MARCA_FIN in _sin_tildes(_valor(*(_celdas(filas[r]).get("A", ("", None, ""))[:2]), compartidos))),
        None,
    )
    if fin is None:
        raise ProcesamientoError(
            "No se encontró la sección «Datos del abono con cheque de gerencia» en la plantilla."
        )
    return _Plantilla(ruta, xml, filas, fin)


def validar_plantilla(contenido: bytes) -> int:
    """Revisa que sea la plantilla del banco y devuelve cuántas filas de abonos
    admite (hasta la sección de cheques)."""
    p = _abrir_plantilla(contenido)
    return p.fin - FILA_DATOS


def generar_macro(plantilla: bytes, abonos: list[Abono], moneda: str, fecha: date) -> bytes:
    """La plantilla con la fila 7 y los abonos llenos; lo demás, intacto."""
    p = _abrir_plantilla(plantilla)
    filas_macro = _filas_macro(abonos, moneda)
    capacidad = p.fin - FILA_DATOS
    if len(filas_macro) > capacidad:
        raise ProcesamientoError(
            f"Son {len(filas_macro)} filas y la plantilla solo admite {capacidad}."
        )

    # Formato de una fila de abono ('A') y de una de documento ('D'): los de las
    # dos primeras filas de datos de la plantilla.
    modelo = {
        "A": p.filas.get(FILA_DATOS, f'<row r="{FILA_DATOS}"/>'),
        "D": p.filas.get(FILA_DATOS + 1, f'<row r="{FILA_DATOS + 1}"/>'),
    }
    estilos = {k: {c: _estilo(a) for c, (a, _v, _x) in _celdas(x).items()} for k, x in modelo.items()}
    atributos = {k: _atributos_fila(x) for k, x in modelo.items()}

    nuevas: dict[int, str] = {}
    for r, xml in p.filas.items():
        if FILA_DATOS <= r < p.fin:
            nuevas[r] = _vaciar(xml)       # restos de una semana anterior, si los hay
        else:
            nuevas[r] = xml
    for i, (tipo, valores) in enumerate(filas_macro):
        r = FILA_DATOS + i
        celdas = "".join(_celda(c, r, estilos[tipo].get(c), valores.get(c)) for c in COLUMNAS)
        nuevas[r] = f'<row r="{r}"{atributos[tipo]}>{celdas}</row>'

    total = round(sum(ab.total for ab in abonos), 2)
    nuevas[FILA_CARGO] = _poner_celdas(
        p.filas.get(FILA_CARGO, f'<row r="{FILA_CARGO}"/>'), FILA_CARGO,
        {"B": f"{len(abonos):06d}", "C": fecha.strftime("%Y%m%d"), "F": _monto(total)},
    )

    datos = re.search(r"(<sheetData\b[^>]*>)(.*?)(</sheetData>)", p.xml, re.S)
    cuerpo = "".join(nuevas[r] for r in sorted(nuevas))
    xml = p.xml[: datos.start(2)] + cuerpo + p.xml[datos.end(2):]

    salida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(plantilla)) as zin, \
            zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            contenido = xml.encode("utf-8") if item.filename == p.ruta else zin.read(item.filename)
            zout.writestr(item, contenido)
    return salida.getvalue()
