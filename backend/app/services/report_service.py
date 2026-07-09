import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.report import Report, ReportStatus
from app.repositories.report_repository import ReportRepository
from app.schemas.report import FinanceRow
from app.services.excel_service import ExcelService

logger = logging.getLogger(__name__)


class ReportNotFoundError(Exception):
    """Raised when a report does not exist."""


class ReportService:
    """Orchestrates report creation and Excel generation."""

    def __init__(self, db: Session):
        self.repo = ReportRepository(db)
        self.excel = ExcelService()

    def create_report(self, name: str, rows: list[FinanceRow]) -> Report:
        report = self.repo.create(name=name)
        try:
            filename = f"report_{report.id}.xlsx"
            output_path = Path(settings.REPORTS_DIR) / filename
            self.excel.build_report(name=name, rows=rows, output_path=output_path)
            return self.repo.update_status(
                report, ReportStatus.COMPLETED, file_path=str(output_path)
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to generate report %s", report.id)
            return self.repo.update_status(
                report, ReportStatus.FAILED, error=str(exc)
            )

    def get_report(self, report_id: int) -> Report:
        report = self.repo.get(report_id)
        if report is None:
            raise ReportNotFoundError(f"Report {report_id} not found")
        return report

    def list_reports(self, skip: int = 0, limit: int = 100) -> list[Report]:
        return self.repo.list(skip=skip, limit=limit)

    def delete_report(self, report_id: int) -> None:
        report = self.get_report(report_id)
        if report.file_path:
            Path(report.file_path).unlink(missing_ok=True)
        self.repo.delete(report)
