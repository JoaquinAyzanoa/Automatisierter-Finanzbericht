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
    # Reasignaciones manuales: id de fila (como texto) -> posición de operación.
    overrides: dict[str, int] = {}
