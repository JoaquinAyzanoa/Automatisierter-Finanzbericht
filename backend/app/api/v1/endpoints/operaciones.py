from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.operacion import OperacionCreate, OperacionRead, OperacionUpdate
from app.services.operacion_service import (
    OperacionNotFoundError,
    OperacionService,
)

router = APIRouter(prefix="/operaciones", tags=["operaciones"])


@router.get("", response_model=list[OperacionRead])
def listar(current_user: CurrentUser, db: DbSession) -> list[OperacionRead]:
    return OperacionService(db).list()


@router.post("", response_model=OperacionRead, status_code=status.HTTP_201_CREATED)
def crear(
    payload: OperacionCreate, current_user: CurrentUser, db: DbSession
) -> OperacionRead:
    return OperacionService(db).create(payload)


@router.put("", response_model=list[OperacionRead])
def reemplazar(
    payload: list[OperacionCreate], current_user: CurrentUser, db: DbSession
) -> list[OperacionRead]:
    """Reemplaza toda la lista (guardado en bloque desde Configuración)."""
    return OperacionService(db).replace_all(payload)


@router.put("/{operacion_id}", response_model=OperacionRead)
def actualizar(
    operacion_id: int,
    payload: OperacionUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> OperacionRead:
    try:
        return OperacionService(db).update(operacion_id, payload)
    except OperacionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Operación no encontrada"
        )


@router.delete("/{operacion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    operacion_id: int, current_user: CurrentUser, db: DbSession
) -> None:
    try:
        OperacionService(db).delete(operacion_id)
    except OperacionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Operación no encontrada"
        )
