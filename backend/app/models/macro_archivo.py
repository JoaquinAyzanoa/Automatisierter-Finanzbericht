from datetime import datetime, timezone

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MacroArchivo(Base):
    """Archivos que se suben para generar las macros de pago masivo del BCP: la
    plantilla .xlsm de cada moneda y su base de cuentas. Una fila por tipo
    ('plantilla_SOL', 'plantilla_USD', 'bd_SOL', 'bd_USD'); subir otra vez el
    mismo tipo la reemplaza."""

    __tablename__ = "macro_archivos"

    tipo: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    contenido: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # Resumen para mostrar en pantalla: "182 cuentas" / "admite 1670 filas".
    detalle: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    subido_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
