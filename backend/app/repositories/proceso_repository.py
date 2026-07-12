from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.proceso import Proceso


class ProcesoRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, proceso: Proceso) -> Proceso:
        self.db.add(proceso)
        self.db.commit()
        self.db.refresh(proceso)
        return proceso

    def get(self, proceso_id: str) -> Proceso | None:
        return self.db.get(Proceso, proceso_id)

    def list(self) -> list[Proceso]:
        stmt = select(Proceso).order_by(Proceso.updated_at.desc())
        return list(self.db.scalars(stmt).all())

    def latest(self) -> Proceso | None:
        stmt = select(Proceso).order_by(Proceso.updated_at.desc()).limit(1)
        return self.db.scalars(stmt).first()

    def save(self, proceso: Proceso) -> Proceso:
        self.db.commit()
        self.db.refresh(proceso)
        return proceso
