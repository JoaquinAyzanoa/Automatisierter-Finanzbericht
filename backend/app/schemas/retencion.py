from pydantic import BaseModel, ConfigDict


class RetencionConfigSchema(BaseModel):
    """Configuración de retención (lectura y guardado)."""

    model_config = ConfigDict(from_attributes=True)

    # Prende/apaga el cálculo de la retención.
    activo: bool = True
    # RUCs de proveedores que son agentes de retención (no se les retiene).
    rucs: list[str] = []
    # Tipo de cambio para convertir importes en dólares a soles (umbral S/ 700).
    tipo_cambio: float = 3.75
