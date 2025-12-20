from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CurrencyBase(BaseModel):
    code: str
    name: str
    value: float
    previous: float
    nominal: int = 1


class CurrencyCreate(CurrencyBase):
    pass


class CurrencyUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = None
    previous: Optional[float] = None
    nominal: Optional[int] = None


class CurrencyRead(CurrencyBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class CurrencyHistoryRead(BaseModel):
    id: int
    currency_id: int
    value: float
    previous: float
    checked_at: datetime

    class Config:
        from_attributes = True