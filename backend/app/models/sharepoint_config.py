from sqlalchemy import JSON, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SharepointConfig(Base):
    """Configuración de SharePoint (fila única, id=1).

    `link_principal` es la carpeta general (ej. .../2026/1. COMPRAS) y `meses`
    mapea el número de mes a su nombre de carpeta: {"1": "1. ENERO", ...}.
    """

    __tablename__ = "sharepoint_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    link_principal: Mapped[str | None] = mapped_column(Text, nullable=True)
    meses: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
