from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Proceso(Base):
    """Un proceso guardado: snapshot del merge clasificado + estado del informe."""

    __tablename__ = "procesos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    # Rango de fechas del filtro (ISO YYYY-MM-DD), guardado al descargar.
    fecha_inicio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fecha_final: Mapped[str | None] = mapped_column(String(10), nullable=True)
    n_filas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Snapshot JSON: columnas, filas, operaciones, fecha_columna.
    payload: Mapped[str] = mapped_column(Text, nullable=False)
