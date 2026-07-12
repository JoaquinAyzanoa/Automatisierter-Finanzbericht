from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProcesoResumen(BaseModel):
    """Fila del historial."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
    fecha_inicio: str | None
    fecha_final: str | None
    n_filas: int


class GuardarProceso(BaseModel):
    """Estado a guardar al descargar el informe."""

    fecha_inicio: str | None = None
    fecha_final: str | None = None
    # id de fila (texto) -> posición de operación, o None para "Otros" (sin categoría).
    overrides: dict[str, int | None] = {}
