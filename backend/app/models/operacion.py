from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Operacion(Base):
    __tablename__ = "operaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    texto: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), default="SOL", nullable=False)
    ambito: Mapped[str] = mapped_column(String(10), default="Nacional", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    # Respetar el filtro de fechas de Informes (si no, sus filas no van a "Otros").
    respeta_filtro: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # Aplicar retención a las filas de esta operación (bienes sí; servicios no).
    aplica_retencion: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
