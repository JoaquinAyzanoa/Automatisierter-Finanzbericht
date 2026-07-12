from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, DbSession
from app.services import clasificacion_service, merge_service
from app.services.operacion_service import OperacionService

router = APIRouter(prefix="/informes", tags=["informes"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.get("/merge")
def merge_clasificado(current_user: CurrentUser, db: DbSession) -> dict:
    path = merge_service.avance_path()
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aún no hay merge generado. Procesa los archivos primero.",
        )
    operaciones = OperacionService(db).list()
    return clasificacion_service.clasificar_merge(path, operaciones)


@router.get("/merge/descargar")
def descargar_clasificado(current_user: CurrentUser, db: DbSession) -> FileResponse:
    path = merge_service.avance_path()
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aún no hay merge generado.",
        )
    operaciones = OperacionService(db).list()
    output = clasificacion_service.escribir_clasificado(path, operaciones)
    return FileResponse(
        output,
        media_type=XLSX_MEDIA_TYPE,
        filename="informe_clasificado.xlsx",
    )
