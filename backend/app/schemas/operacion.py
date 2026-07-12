from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Moneda = Literal["SOL", "USD"]


class OperacionCreate(BaseModel):
    texto: str = Field(default="", max_length=255)
    moneda: Moneda = "SOL"


class OperacionUpdate(BaseModel):
    texto: str | None = Field(default=None, max_length=255)
    moneda: Moneda | None = None


class OperacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    texto: str
    moneda: Moneda
    created_at: datetime
