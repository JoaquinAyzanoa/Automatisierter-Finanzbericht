from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.report import ReportCreate, ReportRead
from app.services.report_service import ReportNotFoundError, ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate, db: Session = Depends(get_db)) -> ReportRead:
    service = ReportService(db)
    report = service.create_report(name=payload.name, rows=payload.rows)
    return report


@router.get("", response_model=list[ReportRead])
def list_reports(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
) -> list[ReportRead]:
    return ReportService(db).list_reports(skip=skip, limit=limit)


@router.get("/{report_id}", response_model=ReportRead)
def get_report(report_id: int, db: Session = Depends(get_db)) -> ReportRead:
    try:
        return ReportService(db).get_report(report_id)
    except ReportNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)) -> FileResponse:
    try:
        report = ReportService(db).get_report(report_id)
    except ReportNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if not report.file_path or not Path(report.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report file not available"
        )

    return FileResponse(
        path=report.file_path,
        media_type=XLSX_MEDIA_TYPE,
        filename=f"{report.name}.xlsx",
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, db: Session = Depends(get_db)) -> None:
    try:
        ReportService(db).delete_report(report_id)
    except ReportNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
