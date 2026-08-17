from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.operacion import Operacion


class OperacionRepository:
    """Data-access layer for Operacion."""

    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Operacion]:
        stmt = select(Operacion).order_by(Operacion.id)
        return list(self.db.scalars(stmt).all())

    def get(self, operacion_id: int) -> Operacion | None:
        return self.db.get(Operacion, operacion_id)

    def create(
        self,
        texto: str,
        moneda: str,
        ambito: str,
        tags: list[str] | None = None,
        respeta_filtro: bool = True,
        aplica_retencion: bool = True,
    ) -> Operacion:
        operacion = Operacion(
            texto=texto,
            moneda=moneda,
            ambito=ambito,
            tags=tags or [],
            respeta_filtro=respeta_filtro,
            aplica_retencion=aplica_retencion,
        )
        self.db.add(operacion)
        self.db.commit()
        self.db.refresh(operacion)
        return operacion

    def update(
        self,
        operacion: Operacion,
        texto: str | None = None,
        moneda: str | None = None,
        ambito: str | None = None,
        tags: list[str] | None = None,
        respeta_filtro: bool | None = None,
        aplica_retencion: bool | None = None,
    ) -> Operacion:
        if texto is not None:
            operacion.texto = texto
        if moneda is not None:
            operacion.moneda = moneda
        if ambito is not None:
            operacion.ambito = ambito
        if tags is not None:
            operacion.tags = tags
        if respeta_filtro is not None:
            operacion.respeta_filtro = respeta_filtro
        if aplica_retencion is not None:
            operacion.aplica_retencion = aplica_retencion
        self.db.commit()
        self.db.refresh(operacion)
        return operacion

    def delete(self, operacion: Operacion) -> None:
        self.db.delete(operacion)
        self.db.commit()

    def replace_all(
        self, items: list[tuple[str, str, str, list[str], bool, bool]]
    ) -> list[Operacion]:
        """Reemplaza toda la lista de operaciones en una sola transacción."""
        self.db.execute(delete(Operacion))
        for texto, moneda, ambito, tags, respeta_filtro, aplica_retencion in items:
            self.db.add(
                Operacion(
                    texto=texto,
                    moneda=moneda,
                    ambito=ambito,
                    tags=tags,
                    respeta_filtro=respeta_filtro,
                    aplica_retencion=aplica_retencion,
                )
            )
        self.db.commit()
        return self.list()
