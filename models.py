from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Currency(SQLModel, table=True):
    __tablename__ = "currencies"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, unique=True)
    name: str = Field(max_length=100)
    value: float = Field()
    previous: float = Field()
    nominal: int = Field(default=1)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CurrencyHistory(SQLModel, table=True):
    __tablename__ = "currency_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    currency_id: int = Field(foreign_key="currencies.id")
    value: float = Field()
    previous: float = Field()
    checked_at: datetime = Field(default_factory=datetime.utcnow)