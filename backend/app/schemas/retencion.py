from pydantic import BaseModel, ConfigDict


class RetencionConfigSchema(BaseModel):
    """Configuración de retención (lectura y guardado)."""

    model_config = ConfigDict(from_attributes=True)

    # Prende/apaga el cálculo de la retención.
    activo: bool = True
    # RUCs de proveedores que son agentes de retención (no se les retiene).
    rucs: list[str] = []


class RucsImportados(BaseModel):
    """RUCs leídos de un archivo, para agregarlos a la lista, y lo que quedó
    fuera (para cuadrar el total con el archivo)."""

    rucs: list[str]
    # Veces que un RUC venía repetido en el archivo.
    repetidos: int = 0
    # Números que no son un RUC de 11 dígitos.
    invalidos: list[str] = []
