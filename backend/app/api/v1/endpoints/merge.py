from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser
from app.services import merge_service
from app.services.excel_utils import ProcesamientoError

router = APIRouter(prefix="/merge", tags=["merge"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.post("/procesar")
def procesar(current_user: CurrentUser) -> dict:
    try:
        result = merge_service.process_merge()
    except ProcesamientoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    return {
        "rows": result["rows"],
        "mensaje": f"Merge generado: {result['rows']} filas.",
    }


@router.get("/avance")
def descargar_avance(current_user: CurrentUser) -> FileResponse:
    path = merge_service.avance_path()
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aún no hay avance generado.",
        )
    return FileResponse(
        path,
        media_type=XLSX_MEDIA_TYPE,
        filename="merge_avance.xlsx",
    )
