from sqlalchemy import JSON, Boolean, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetencionConfig(Base):
    """Configuración de la retención de IGV (fila única, id=1).

    `activo` prende/apaga el cálculo de la retención. `rucs` son los RUCs de
    proveedores que SON agentes de retención: a ellos no se les retiene
    (excepción). `tipo_cambio` convierte el importe en dólares a soles para
    compararlo contra el umbral de S/ 700 (ver detalle_export).
    """

    __tablename__ = "retencion_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rucs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    tipo_cambio: Mapped[float] = mapped_column(Float, default=3.75, nullable=False)
