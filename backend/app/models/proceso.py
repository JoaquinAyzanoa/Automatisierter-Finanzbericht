from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Proceso(Base):
    """Un proceso guardado: snapshot del merge clasificado + estado del informe."""

    __tablename__ = "procesos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # Nombre editable que el usuario le pone al proceso en el Historial.
    nombre: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    # Rango de fechas del filtro (ISO YYYY-MM-DD), guardado al descargar.
    fecha_inicio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fecha_final: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Tipo de cambio (S/ por US$) editable en Informes; va a la retención y al
    # Resumen (celda C18). Si es None se usa el valor por defecto.
    tipo_cambio: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_filas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Snapshot JSON: columnas, filas, operaciones, fecha_columna.
    payload: Mapped[str] = mapped_column(Text, nullable=False)
