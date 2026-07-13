from pydantic import BaseModel, ConfigDict


class SharepointConfigSchema(BaseModel):
    """Configuración de SharePoint (lectura y guardado)."""

    model_config = ConfigDict(from_attributes=True)

    link_principal: str | None = None
    # número de mes (str) -> nombre de carpeta, ej. {"7": "7. JULIO"}.
    meses: dict[str, str] = {}
