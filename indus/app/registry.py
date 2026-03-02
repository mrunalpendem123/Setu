from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .db import Base, engine, IndusmerchantModel as MerchantRecord


def init_registry() -> None:
    Base.metadata.create_all(bind=engine)


class MerchantRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    base_url: str
    upi_vpa: Optional[str] = None
    razorpay_account_id: Optional[str] = None
    product_feed_url: Optional[str] = None


class MerchantResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    base_url: str
    upi_vpa: Optional[str] = None
    razorpay_account_id: Optional[str] = None
    product_feed_url: Optional[str] = None
    created_at: datetime
