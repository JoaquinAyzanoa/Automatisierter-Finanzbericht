from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Moneda = Literal["SOL", "USD"]
Ambito = Literal["Nacional", "Exterior"]


class OperacionCreate(BaseModel):
    texto: str = Field(default="", max_length=255)
    moneda: Moneda = "SOL"
    ambito: Ambito = "Nacional"


class OperacionUpdate(BaseModel):
    texto: str | None = Field(default=None, max_length=255)
    moneda: Moneda | None = None
    ambito: Ambito | None = None


class OperacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    texto: str
    moneda: Moneda
    ambito: Ambito
    created_at: datetime
