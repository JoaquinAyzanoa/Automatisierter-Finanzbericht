from sqlalchemy import JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgenteAduanaConfig(Base):
    """Configuración de agentes de aduana (fila única, id=1).

    `rucs` es la lista de RUCs de los agentes aduaneros. Cuando las facturas de
    una misma Orden de Compra (N° O/C-O/S) incluyen a alguno de estos RUCs, todo
    el grupo se consolida y se deposita al agente (ver detalle_export).
    """

    __tablename__ = "agente_aduana_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rucs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
