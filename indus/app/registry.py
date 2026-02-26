from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime
from pydantic import BaseModel, ConfigDict

from .db import Base, SessionLocal, engine


class MerchantRecord(Base):
    __tablename__ = "indus_merchants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    product_feed_url = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def init_registry() -> None:
    Base.metadata.create_all(bind=engine)


class MerchantRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    base_url: str
    product_feed_url: Optional[str] = None


class MerchantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    base_url: str
    product_feed_url: Optional[str] = None
    created_at: datetime
