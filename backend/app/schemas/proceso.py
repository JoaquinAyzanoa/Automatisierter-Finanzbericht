from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProcesoResumen(BaseModel):
    """Fila del historial."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str | None
    created_at: datetime
    updated_at: datetime
    fecha_inicio: str | None
    fecha_final: str | None
    n_filas: int


class RenombrarProceso(BaseModel):
    """Nombre editable del proceso en el Historial."""

    nombre: str | None = None


class GuardarProceso(BaseModel):
    """Estado a guardar al descargar el informe."""

    fecha_inicio: str | None = None
    fecha_final: str | None = None
    # Tipo de cambio (S/ por US$); si es None se mantiene el guardado.
    tipo_cambio: float | None = None
    # id de fila (texto) -> posición de operación, o None para "Otros" (sin categoría).
    overrides: dict[str, int | None] = {}
