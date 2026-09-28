from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.retencion import RetencionConfigSchema, RucsImportados
from app.services.excel_utils import ProcesamientoError
from app.services.retencion_config_service import RetencionConfigService, extraer_rucs

router = APIRouter(prefix="/retencion", tags=["retencion"])


@router.get("", response_model=RetencionConfigSchema)
def obtener(current_user: CurrentUser, db: DbSession) -> RetencionConfigSchema:
    return RetencionConfigService(db).get()


@router.put("", response_model=RetencionConfigSchema)
def guardar(
    payload: RetencionConfigSchema, current_user: CurrentUser, db: DbSession
) -> RetencionConfigSchema:
    return RetencionConfigService(db).save(payload.activo, payload.rucs)


@router.post("/rucs/importar", response_model=RucsImportados)
def importar_rucs(
    current_user: CurrentUser, archivo: UploadFile = File(...)
) -> RucsImportados:
    """Lee los RUC de un Excel (o CSV) y los devuelve. No guarda nada: la
    pantalla los agrega a la lista y el usuario revisa antes de guardar."""
    contenido = archivo.file.read()
    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío."
        )
    try:
        return RucsImportados(**extraer_rucs(contenido, archivo.filename or ""))
    except ProcesamientoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
