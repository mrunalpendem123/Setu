from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, DateTime, Integer
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


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class SessionRecord(Base):
    __tablename__ = "indus_sessions"

    session_id = Column(String, primary_key=True)
    merchant_base_url = Column(String, nullable=False)
    session_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class PaymentRecord(Base):
    __tablename__ = "indus_payments"

    payment_id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class TokenRecord(Base):
    __tablename__ = "indus_tokens"

    token = Column(String, primary_key=True)
    session_id = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)


class OrderEvent(Base):
    __tablename__ = "indus_order_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db():
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
