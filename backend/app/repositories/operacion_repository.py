from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.operacion import Operacion


class OperacionRepository:
    """Data-access layer for Operacion."""

    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Operacion]:
        stmt = select(Operacion).order_by(Operacion.posicion, Operacion.id)
        return list(self.db.scalars(stmt).all())

    def get(self, operacion_id: int) -> Operacion | None:
        return self.db.get(Operacion, operacion_id)

    def _ordenadas(self) -> list[Operacion]:
        """Como `list()`, pero volcando antes lo pendiente: la sesión no hace
        autoflush, y sin esto las consultas devolverían el orden viejo."""
        self.db.flush()
        return self.list()

    def _renumerar(self) -> None:
        """Deja las posiciones en 1..N, sin repetidos ni huecos, respetando el
        orden actual. Es lo que hace que `posicion` sea única: no hay un índice
        UNIQUE en la tabla porque al reordenar dos filas cruzarían valores a
        mitad de la transacción y SQLite lo rechazaría."""
        for i, operacion in enumerate(self._ordenadas(), start=1):
            if operacion.posicion != i:
                operacion.posicion = i

    def _siguiente_posicion(self) -> int:
        return len(self._ordenadas()) + 1

    def create(
        self,
        texto: str,
        moneda: str,
        ambito: str,
        tags: list[str] | None = None,
        respeta_filtro: bool = True,
        aplica_retencion: bool = True,
        posicion: int | None = None,
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
        self.db.flush()
        self._mover(operacion, posicion or self._siguiente_posicion())
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
        posicion: int | None = None,
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
        if posicion is not None and posicion != operacion.posicion:
            self._mover(operacion, posicion)
        else:
            self._renumerar()
        self.db.commit()
        self.db.refresh(operacion)
        return operacion

    def _mover(self, operacion: Operacion, destino: int) -> None:
        """Coloca `operacion` en `destino` corriendo las demás, como al arrastrar
        una fila: las posiciones intermedias se desplazan un lugar. Deja la
        numeración ya en 1..N, así que no hace falta renumerar después."""
        restantes = [o for o in self._ordenadas() if o.id != operacion.id]
        destino = max(1, min(destino, len(restantes) + 1))
        restantes.insert(destino - 1, operacion)
        for i, o in enumerate(restantes, start=1):
            o.posicion = i

    def delete(self, operacion: Operacion) -> None:
        self.db.delete(operacion)
        self.db.flush()
        self._renumerar()
        self.db.commit()

    def replace_all(self, items: list[dict]) -> list[Operacion]:
        """Guarda la lista completa en una sola transacción, en el orden en que
        llega. Las que traen `id` conservan el suyo (así lo que apunte a una
        operación no se rompe al reordenar); las que no, se crean; las que ya no
        están, se borran."""
        existentes = {o.id: o for o in self.list()}
        vistos: set[int] = set()
        resultado: list[Operacion] = []

        for i, item in enumerate(items, start=1):
            operacion = existentes.get(item.get("id") or 0)
            if operacion is None:
                operacion = Operacion()
                self.db.add(operacion)
            else:
                vistos.add(operacion.id)
            operacion.texto = item["texto"]
            operacion.moneda = item["moneda"]
            operacion.ambito = item["ambito"]
            operacion.tags = item["tags"]
            operacion.respeta_filtro = item["respeta_filtro"]
            operacion.aplica_retencion = item["aplica_retencion"]
            operacion.posicion = i
            resultado.append(operacion)

        for operacion_id, operacion in existentes.items():
            if operacion_id not in vistos:
                self.db.delete(operacion)

        self.db.commit()
        return self.list()
