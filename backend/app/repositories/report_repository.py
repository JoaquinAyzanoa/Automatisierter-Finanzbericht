from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import Report, ReportStatus


class ReportRepository:
    """Data-access layer for Report. No business logic here."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str) -> Report:
        report = Report(name=name, status=ReportStatus.PENDING.value)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get(self, report_id: int) -> Report | None:
        return self.db.get(Report, report_id)

    def list(self, skip: int = 0, limit: int = 100) -> list[Report]:
        stmt = (
            select(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def update_status(
        self,
        report: Report,
        status: ReportStatus,
        file_path: str | None = None,
        error: str | None = None,
    ) -> Report:
        report.status = status.value
        report.file_path = file_path
        report.error = error
        self.db.commit()
        self.db.refresh(report)
        return report

    def delete(self, report: Report) -> None:
        self.db.delete(report)
        self.db.commit()
