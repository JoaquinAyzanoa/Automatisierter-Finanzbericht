from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser
from app.services import reporteador_service
from app.services.excel_utils import ProcesamientoError

router = APIRouter(prefix="/reporteador", tags=["reporteador"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.post("/procesar")
def procesar(
    current_user: CurrentUser, archivo: UploadFile = File(...)
) -> dict:
    content = archivo.file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío.",
        )
    try:
        result = reporteador_service.process_reporteador(
            archivo.filename or "", content
        )
    except ProcesamientoError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )

    return {
        "rows": result["rows"],
        "mensaje": f"Reporteador procesado: {result['rows']} filas.",
    }


@router.get("/avance")
def descargar_avance(current_user: CurrentUser) -> FileResponse:
    path = reporteador_service.avance_path()
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aún no hay avance generado.",
        )
    return FileResponse(
        path,
        media_type=XLSX_MEDIA_TYPE,
        filename="reporteador_avance.xlsx",
    )
