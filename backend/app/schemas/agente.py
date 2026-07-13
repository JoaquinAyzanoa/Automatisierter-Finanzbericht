from pydantic import BaseModel, ConfigDict


class AgenteConfigSchema(BaseModel):
    """Configuración de agentes de aduana (lectura y guardado)."""

    model_config = ConfigDict(from_attributes=True)

    # Lista de RUCs de los agentes aduaneros.
    rucs: list[str] = []
