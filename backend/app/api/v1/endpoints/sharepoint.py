from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.sharepoint import SharepointConfigSchema
from app.services.sharepoint_config_service import SharepointConfigService

router = APIRouter(prefix="/sharepoint", tags=["sharepoint"])


@router.get("", response_model=SharepointConfigSchema)
def obtener(current_user: CurrentUser, db: DbSession) -> SharepointConfigSchema:
    return SharepointConfigService(db).get()


@router.put("", response_model=SharepointConfigSchema)
def guardar(
    payload: SharepointConfigSchema, current_user: CurrentUser, db: DbSession
) -> SharepointConfigSchema:
    return SharepointConfigService(db).save(payload.link_principal, payload.meses)
