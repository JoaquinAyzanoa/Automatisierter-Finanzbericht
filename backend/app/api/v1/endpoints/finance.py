from fastapi import APIRouter

from app.schemas.report import FinanceRow

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/sample", response_model=list[FinanceRow])
def sample_data() -> list[FinanceRow]:
    """Sample finance data — placeholder until real data sources are wired in."""
    return [
        FinanceRow(account="Revenue", period="2026-Q1", amount=125000.0),
        FinanceRow(account="COGS", period="2026-Q1", amount=-48000.0),
        FinanceRow(account="Operating Expenses", period="2026-Q1", amount=-32000.0),
    ]
