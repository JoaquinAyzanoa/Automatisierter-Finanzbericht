from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser
from app.services import proveedores_service
from app.services.excel_utils import ProcesamientoError

router = APIRouter(prefix="/proveedores", tags=["proveedores"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.post("/procesar")
def procesar(
    current_user: CurrentUser,
    dolares: UploadFile = File(...),
    soles: UploadFile = File(...),
) -> dict:
    dolares_content = dolares.file.read()
    soles_content = soles.file.read()
    if not dolares_content or not soles_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ambos archivos (DOLARES y SOLES) son obligatorios.",
        )
    try:
        result = proveedores_service.process_proveedores(
            dolares.filename or "",
            dolares_content,
            soles.filename or "",
            soles_content,
        )
    except ProcesamientoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    return {
        "rows": result["rows"],
        "mensaje": f"Proveedores combinados: {result['rows']} filas.",
    }


@router.get("/avance")
def descargar_avance(current_user: CurrentUser) -> FileResponse:
    path = proveedores_service.avance_path()
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aún no hay avance generado.",
        )
    return FileResponse(
        path,
        media_type=XLSX_MEDIA_TYPE,
        filename="proveedores_avance.xlsx",
    )
