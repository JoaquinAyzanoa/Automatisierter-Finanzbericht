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


def extraer_rucs(contenido: bytes, nombre: str) -> tuple[list[str], int]:
    """RUCs de un archivo (.xlsx o texto/CSV), sin repetir y en el orden en que
    aparecen. Se buscan en todas las celdas, así no importa en qué columna
    estén. Devuelve también cuántos valores se descartaron por no ser RUC."""
    textos: list[str] = []
    if nombre.lower().endswith((".xlsx", ".xlsm")):
        try:
            wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
        except Exception as exc:
            raise ProcesamientoError("No se pudo leer el Excel.") from exc
        for hoja in wb.worksheets:
            for fila in hoja.iter_rows(values_only=True):
                textos += [str(v) for v in fila if v not in (None, "")]
        wb.close()
    else:
        try:
            textos = contenido.decode("utf-8-sig", errors="ignore").split()
        except Exception as exc:
            raise ProcesamientoError("No se pudo leer el archivo.") from exc

    rucs: list[str] = []
    descartados = 0
    for texto in textos:
        limpio = normalizar_ruc(texto)
        encontrados = _RUC_RE.findall(limpio)
        if not encontrados:
            descartados += 1
            continue
        for ruc in encontrados:
            if ruc not in rucs:
                rucs.append(ruc)
    if not rucs:
        raise ProcesamientoError("El archivo no tiene ningún RUC de 11 dígitos.")
    return rucs, descartados


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
