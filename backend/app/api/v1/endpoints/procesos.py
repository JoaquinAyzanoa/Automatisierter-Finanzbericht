from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.schemas.proceso import GuardarProceso, ProcesoResumen, RenombrarProceso
from app.services.excel_utils import ProcesamientoError
from app.services.operacion_service import OperacionService
from app.services.proceso_service import ProcesoNotFoundError, ProcesoService

router = APIRouter(prefix="/procesos", tags=["procesos"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.post("")
def crear(current_user: CurrentUser, db: DbSession) -> dict:
    operaciones = OperacionService(db).list()
    try:
        proceso = ProcesoService(db).crear_desde_merge(operaciones)
    except ProcesamientoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    return {"id": proceso.id}


@router.get("", response_model=list[ProcesoResumen])
def listar(current_user: CurrentUser, db: DbSession) -> list[ProcesoResumen]:
    return ProcesoService(db).list()


@router.get("/latest")
def latest(current_user: CurrentUser, db: DbSession) -> dict:
    data = ProcesoService(db).latest()
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No hay procesos."
        )
    return data


@router.get("/{proceso_id}")
def obtener(proceso_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    try:
        return ProcesoService(db).obtener(proceso_id)
    except ProcesoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proceso no encontrado"
        )


@router.post("/{proceso_id}/nombre")
def renombrar(
    proceso_id: str,
    payload: RenombrarProceso,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    try:
        proceso = ProcesoService(db).renombrar(proceso_id, payload.nombre)
    except ProcesoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proceso no encontrado"
        )
    return {"id": proceso.id, "nombre": proceso.nombre}


@router.post("/{proceso_id}/guardar")
def guardar(
    proceso_id: str,
    payload: GuardarProceso,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    try:
        proceso = ProcesoService(db).guardar(
            proceso_id,
            payload.fecha_inicio,
            payload.fecha_final,
            payload.overrides,
        )
    except ProcesoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proceso no encontrado"
        )
    return {"id": proceso.id, "updated_at": proceso.updated_at.isoformat()}


@router.post("/{proceso_id}/descargar")
def descargar(
    proceso_id: str,
    payload: GuardarProceso,
    current_user: CurrentUser,
    db: DbSession,
) -> FileResponse:
    try:
        output = ProcesoService(db).guardar_y_generar_xlsx(
            proceso_id,
            payload.fecha_inicio,
            payload.fecha_final,
            payload.overrides,
        )
    except ProcesoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proceso no encontrado"
        )
    return FileResponse(
        output,
        media_type=XLSX_MEDIA_TYPE,
        filename="informe_clasificado.xlsx",
    )
