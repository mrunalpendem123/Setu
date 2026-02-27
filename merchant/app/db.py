from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import JSON

try:
    from sqlalchemy.dialects.postgresql import JSONB
except Exception:  # pragma: no cover - fallback for non-Postgres
    JSONB = JSON


def _database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is not set")
    return value


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class CheckoutSessionModel(Base):
    __tablename__ = "checkout_sessions"

    id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class OrderModel(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True)
    checkout_session_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class IdempotencyModel(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String, primary_key=True)
    request_hash = Column(String, nullable=False)
    response_body = Column(JSONB, nullable=False)
    status_code = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
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
