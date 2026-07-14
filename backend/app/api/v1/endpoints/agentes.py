from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.agente import AgenteConfigSchema
from app.services.agente_config_service import AgenteConfigService

router = APIRouter(prefix="/agentes", tags=["agentes"])


@router.get("", response_model=AgenteConfigSchema)
def obtener(current_user: CurrentUser, db: DbSession) -> AgenteConfigSchema:
    return AgenteConfigService(db).get()


@router.put("", response_model=AgenteConfigSchema)
def guardar(
    payload: AgenteConfigSchema, current_user: CurrentUser, db: DbSession
) -> AgenteConfigSchema:
    return AgenteConfigService(db).save(payload.rucs, payload.relacionados)
