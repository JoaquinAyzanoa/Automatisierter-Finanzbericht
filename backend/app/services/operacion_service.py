from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.operacion import Operacion
from app.repositories.operacion_repository import OperacionRepository
from app.schemas.operacion import OperacionCreate, OperacionUpdate


class OperacionNotFoundError(Exception):
    """Raised when an operacion does not exist."""


class OperacionService:
    def __init__(self, db: Session):
        self.repo = OperacionRepository(db)

    def list(self) -> list[Operacion]:
        return self.repo.list()

    def create(self, data: OperacionCreate) -> Operacion:
        return self.repo.create(
            texto=data.texto,
            moneda=data.moneda,
            ambito=data.ambito,
            tags=data.tags,
            respeta_filtro=data.respeta_filtro,
        )

    def replace_all(self, items: list[OperacionCreate]) -> list[Operacion]:
        pairs = [
            (item.texto, item.moneda, item.ambito, item.tags, item.respeta_filtro)
            for item in items
        ]
        return self.repo.replace_all(pairs)

    def update(self, operacion_id: int, data: OperacionUpdate) -> Operacion:
        operacion = self.repo.get(operacion_id)
        if operacion is None:
            raise OperacionNotFoundError(f"Operacion {operacion_id} not found")
        return self.repo.update(
            operacion,
            texto=data.texto,
            moneda=data.moneda,
            ambito=data.ambito,
            tags=data.tags,
            respeta_filtro=data.respeta_filtro,
        )

    def delete(self, operacion_id: int) -> None:
        operacion = self.repo.get(operacion_id)
        if operacion is None:
            raise OperacionNotFoundError(f"Operacion {operacion_id} not found")
        self.repo.delete(operacion)
