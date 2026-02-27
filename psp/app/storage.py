from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import JSON

try:
    from sqlalchemy.dialects.postgresql import JSONB
except Exception:  # pragma: no cover
    JSONB = JSON


def _database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is not set")
    return value


Base = declarative_base()
_engine = None
_SessionLocal = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(_database_url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def init_db() -> None:
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)


@contextmanager
def _get_db():
    _get_engine()
    session = _SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DelegatedPaymentToken(Base):
    __tablename__ = "delegated_payment_tokens"

    token_id = Column(String, primary_key=True)
    max_amount = Column(Integer, nullable=False)
    currency = Column(String, nullable=False)
    checkout_session_id = Column(String, nullable=False)
    merchant_id = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)


@dataclass
class TokenRecord:
    token_id: str
    max_amount: int
    currency: str
    checkout_session_id: str
    merchant_id: str
    expires_at: datetime
    status: str
    created_at: datetime
    used_at: Optional[datetime]
    metadata: Dict[str, Any]


def _to_record(row: DelegatedPaymentToken) -> TokenRecord:
    return TokenRecord(
        token_id=row.token_id,
        max_amount=row.max_amount,
        currency=row.currency,
        checkout_session_id=row.checkout_session_id,
        merchant_id=row.merchant_id,
        expires_at=row.expires_at,
        status=row.status,
        created_at=row.created_at,
        used_at=row.used_at,
        metadata=row.metadata_ or {},
    )


def save_token(record: TokenRecord) -> None:
    with _get_db() as db:
        row = db.get(DelegatedPaymentToken, record.token_id)
        if row:
            row.status = record.status
            row.used_at = record.used_at
        else:
            row = DelegatedPaymentToken(
                token_id=record.token_id,
                max_amount=record.max_amount,
                currency=record.currency,
                checkout_session_id=record.checkout_session_id,
                merchant_id=record.merchant_id,
                expires_at=record.expires_at,
                status=record.status,
                created_at=record.created_at,
                used_at=record.used_at,
                metadata_=record.metadata,
            )
            db.add(row)
        db.commit()


def get_token(token_id: str) -> Optional[TokenRecord]:
    with _get_db() as db:
        row = db.get(DelegatedPaymentToken, token_id)
        if not row:
            return None
        return _to_record(row)
