from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.retencion import RetencionConfigSchema
from app.services.retencion_config_service import RetencionConfigService

router = APIRouter(prefix="/retencion", tags=["retencion"])


@router.get("", response_model=RetencionConfigSchema)
def obtener(current_user: CurrentUser, db: DbSession) -> RetencionConfigSchema:
    return RetencionConfigService(db).get()


@router.put("", response_model=RetencionConfigSchema)
def guardar(
    payload: RetencionConfigSchema, current_user: CurrentUser, db: DbSession
) -> RetencionConfigSchema:
    return RetencionConfigService(db).save(payload.activo, payload.rucs)
