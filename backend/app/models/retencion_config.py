from sqlalchemy import JSON, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RetencionConfig(Base):
    """Configuración de la retención de IGV (fila única, id=1).

    `rucs` son los RUCs de proveedores que SON agentes de retención: a ellos no
    se les retiene (excepción). `tipo_cambio` convierte el importe en dólares a
    soles para compararlo contra el umbral de S/ 700 (ver detalle_export).
    """

    __tablename__ = "retencion_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rucs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    tipo_cambio: Mapped[float] = mapped_column(Float, default=3.75, nullable=False)
