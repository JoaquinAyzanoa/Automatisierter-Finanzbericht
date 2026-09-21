from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TipoArchivo = Literal["plantilla_SOL", "plantilla_USD", "bd_SOL", "bd_USD"]
Moneda = Literal["SOL", "USD"]


class MacroArchivoRead(BaseModel):
    tipo: TipoArchivo
    nombre: str | None = None
    detalle: str = ""
    subido_en: datetime | None = None


class DocumentoPago(BaseModel):
    numero: str
    monto: float


class AbonoPago(BaseModel):
    ruc: str
    nombre: str
    tipo_cuenta: str
    cuenta: str
    en_bd: bool
    total: float
    documentos: list[DocumentoPago]


class MacroMoneda(BaseModel):
    moneda: Moneda
    abonos: list[AbonoPago]
    total: float
    n_documentos: int
    sin_cuenta: int
    # Falta subir la plantilla o la base de esta moneda.
    faltan: list[str]


class VistaPreviaMacros(BaseModel):
    proceso_id: str
    monedas: list[MacroMoneda]
