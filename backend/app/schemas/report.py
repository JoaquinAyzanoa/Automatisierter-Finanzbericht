from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import ReportStatus


class FinanceRow(BaseModel):
    """A single line of finance data to include in the report."""

    account: str = Field(..., examples=["Revenue"])
    period: str = Field(..., examples=["2026-Q1"])
    amount: float = Field(..., examples=[15000.50])


class ReportCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Q1 Finance Report"])
    rows: list[FinanceRow] = Field(default_factory=list)


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: ReportStatus
    file_path: str | None
    error: str | None
    created_at: datetime
