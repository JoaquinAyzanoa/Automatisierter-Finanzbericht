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
    # Veces que un identificador venía repetido en el archivo.
    repetidos: int = 0
    # Los que no tienen 11 dígitos: entran igual (pueden ser del exterior),
    # pero se muestran para revisarlos.
    dudosos: list[str] = []
