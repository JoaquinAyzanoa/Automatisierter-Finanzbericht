import io
import re

import openpyxl
from sqlalchemy.orm import Session

from app.models.retencion_config import RetencionConfig
from app.services.agente_config_service import normalizar_ruc
from app.services.excel_utils import ProcesamientoError

DEFAULT_TIPO_CAMBIO = 3.75
# Un RUC son 11 dígitos; lo demás que venga en el archivo se descarta.
_RUC_RE = re.compile(r"\b\d{11}\b")


def _celdas(contenido: bytes, nombre: str) -> list[list[str]]:
    """El archivo como filas de textos (.xlsx/.xlsm o texto/CSV)."""
    if nombre.lower().endswith((".xlsx", ".xlsm")):
        try:
            wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
        except Exception as exc:
            raise ProcesamientoError("No se pudo leer el Excel.") from exc
        filas = [
            [_texto_celda(v) for v in fila]
            for hoja in wb.worksheets
            for fila in hoja.iter_rows(values_only=True)
        ]
        wb.close()
        return filas
    try:
        texto = contenido.decode("utf-8-sig", errors="ignore")
    except Exception as exc:
        raise ProcesamientoError("No se pudo leer el archivo.") from exc
    return [re.split(r"[;,\t ]+", linea.strip()) for linea in texto.splitlines()]


def _texto_celda(v) -> str:
    """El valor de la celda como texto. Un RUC guardado como número llega como
    float (2.34075E+12 en Excel) y hay que escribirlo entero, no en notación
    científica, para poder avisar de él."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return f"{int(v)}"
    return str(v).strip()


def extraer_rucs(contenido: bytes, nombre: str) -> dict:
    """RUCs de un archivo, sin repetir y en el orden en que aparecen.

    Se busca la columna que trae los RUC (la que tiene más) y se revisa entera,
    para poder avisar de sus valores malos: un RUC de menos dígitos, un DNI, o
    uno que Excel guardó como número y quedó en notación científica. Si ninguna
    columna destaca, se buscan RUCs en todas las celdas.

    Además del listado se informa qué quedó fuera, para cuadrar con el archivo:
      - `repetidos`: RUCs que aparecen más de una vez.
      - `invalidos`: valores de la columna de RUC que no son un RUC de 11 dígitos.
    """
    filas = _celdas(contenido, nombre)
    aciertos: dict[int, int] = {}
    for fila in filas:
        for i, celda in enumerate(fila):
            if _RUC_RE.fullmatch(normalizar_ruc(celda)):
                aciertos[i] = aciertos.get(i, 0) + 1
    columna = max(aciertos, key=lambda i: aciertos[i]) if aciertos else None

    rucs: list[str] = []
    repetidos = 0
    invalidos: list[str] = []
    for fila in filas:
        # La columna de RUC se revisa entera; del resto solo se toman los RUC.
        if columna is None:
            celdas = fila
        elif columna < len(fila):
            celdas = [fila[columna]]
        else:
            celdas = []
        for celda in celdas:
            limpio = normalizar_ruc(celda)
            if not limpio:
                continue
            if _RUC_RE.fullmatch(limpio):
                if limpio in rucs:
                    repetidos += 1
                else:
                    rucs.append(limpio)
            elif any(c.isdigit() for c in limpio):
                invalidos.append(limpio)
        if columna is not None:
            # Por si algún RUC quedó en otra columna de esa misma fila.
            for i, celda in enumerate(fila):
                if i == columna:
                    continue
                limpio = normalizar_ruc(celda)
                if _RUC_RE.fullmatch(limpio) and limpio not in rucs:
                    rucs.append(limpio)
    if not rucs:
        raise ProcesamientoError("El archivo no tiene ningún RUC de 11 dígitos.")
    return {"rucs": rucs, "repetidos": repetidos, "invalidos": invalidos}


class RetencionConfigService:
    """Gestiona la fila única de configuración de retención."""

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> RetencionConfig:
        cfg = self.db.get(RetencionConfig, 1)
        if cfg is None:
            cfg = RetencionConfig(
                id=1, activo=True, rucs=[], tipo_cambio=DEFAULT_TIPO_CAMBIO
            )
            self.db.add(cfg)
            self.db.commit()
            self.db.refresh(cfg)
        return cfg

    def save(self, activo, rucs: list[str]) -> RetencionConfig:
        cfg = self.get()
        cfg.activo = bool(activo)
        limpios: list[str] = []
        for r in rucs or []:
            n = normalizar_ruc(r)
            if n and n not in limpios:
                limpios.append(n)
        cfg.rucs = limpios
        self.db.commit()
        self.db.refresh(cfg)
        return cfg

    def as_dict(self) -> dict:
        cfg = self.get()
        return {
            "activo": bool(cfg.activo),
            "rucs": list(cfg.rucs or []),
        }
