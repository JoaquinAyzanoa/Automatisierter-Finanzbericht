from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import Response

from app.api.deps import CurrentUser, DbSession
from app.schemas.macro import MacroArchivoRead, Moneda, TipoArchivo, VistaPreviaMacros
from app.services.excel_utils import ProcesamientoError
from app.services.macro_service import MacroService
from app.services.proceso_service import ProcesoNotFoundError

router = APIRouter(prefix="/macros", tags=["macros"])

XLSM_MEDIA_TYPE = "application/vnd.ms-excel.sheet.macroEnabled.12"


@router.get("/archivos", response_model=list[MacroArchivoRead])
def listar_archivos(current_user: CurrentUser, db: DbSession) -> list[dict]:
    return MacroService(db).estado()


@router.post("/archivos/{tipo}", response_model=MacroArchivoRead)
def subir_archivo(
    tipo: TipoArchivo,
    current_user: CurrentUser,
    db: DbSession,
    archivo: UploadFile = File(...),
) -> dict:
    contenido = archivo.file.read()
    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío."
        )
    try:
        return MacroService(db).subir(tipo, archivo.filename or "", contenido)
    except ProcesamientoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


@router.get("/procesos/{proceso_id}", response_model=VistaPreviaMacros)
def vista_previa(proceso_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    """A quién se le paga, cuánto y a qué cuenta, antes de descargar."""
    try:
        return MacroService(db).vista_previa(proceso_id)
    except ProcesoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proceso no encontrado"
        )
    except ProcesamientoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


@router.get("/procesos/{proceso_id}/descargar")
def descargar(
    proceso_id: str,
    moneda: Moneda,
    fecha: date,
    current_user: CurrentUser,
    db: DbSession,
) -> Response:
    """La macro de una moneda, llena y lista para ejecutar."""
    try:
        contenido, nombre = MacroService(db).generar(proceso_id, moneda, fecha)
    except ProcesoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Proceso no encontrado"
        )
    except ProcesamientoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    return Response(
        content=contenido,
        media_type=XLSM_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nombre)}"},
    )
