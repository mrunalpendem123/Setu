from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.types import JSON

try:
    from sqlalchemy.dialects.postgresql import JSONB
except Exception:  # pragma: no cover
    JSONB = JSON

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from .security import validate_request
from .storage import TokenRecord, save_token, get_token, init_db


app = FastAPI(title="ACP Delegated Payment PSP (Stub)", version="0.3.0")


# ---------------------------------------------------------------------------
# DB-backed idempotency store
# ---------------------------------------------------------------------------

_idem_Base = declarative_base()


class _IdempotencyRow(_idem_Base):
    __tablename__ = "psp_idempotency_keys"
    key = Column(String, primary_key=True)
    request_hash = Column(String, nullable=False)
    response_body = Column(JSONB, nullable=False)
    status_code = Column(Integer, nullable=False)


_idem_engine = None
_idem_Session = None


def _idem_engine_init():
    global _idem_engine, _idem_Session
    if _idem_engine is None:
        url = os.getenv("DATABASE_URL")
        if url:
            _idem_engine = create_engine(url, pool_pre_ping=True)
            _idem_Session = sessionmaker(bind=_idem_engine, autocommit=False, autoflush=False)
            _idem_Base.metadata.create_all(bind=_idem_engine)


@contextmanager
def _idem_db():
    _idem_engine_init()
    if _idem_Session is None:
        yield None
        return
    session = _idem_Session()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.on_event("startup")
def _startup() -> None:
    try:
        init_db()
        _idem_engine_init()
    except Exception:
        pass  # Startup continues even if DB is not available


def _error(code: str, message: str, status: int = 400) -> JSONResponse:
    payload = {"error": {"type": "invalid_request", "code": code, "message": message}}
    return JSONResponse(content=payload, status_code=status)


def _parse_iso(dt: str) -> datetime:
    return datetime.fromisoformat(dt.replace("Z", "+00:00"))


def _idempotency_key(request: Request) -> str | None:
    return request.headers.get("Idempotency-Key")


def _request_hash(method: str, path: str, body: bytes) -> str:
    hasher = hashlib.sha256()
    hasher.update(method.encode())
    hasher.update(b"|")
    hasher.update(path.encode())
    hasher.update(b"|")
    hasher.update(body)
    return hasher.hexdigest()


def _apply_idempotency(request: Request, body: bytes, payload: dict, status_code: int) -> JSONResponse:
    key = _idempotency_key(request)
    if not key:
        return JSONResponse(content=payload, status_code=status_code)

    req_hash = _request_hash(request.method, request.url.path, body)

    with _idem_db() as db:
        if db is not None:
            existing = db.get(_IdempotencyRow, key)
            if existing:
                if existing.request_hash != req_hash:
                    return _error("request_not_idempotent", "Idempotency key conflict", status=409)
                return JSONResponse(content=existing.response_body, status_code=existing.status_code)
            db.add(_IdempotencyRow(key=key, request_hash=req_hash, response_body=payload, status_code=status_code))
            db.commit()

    return JSONResponse(content=payload, status_code=status_code)


def _validate_delegate_request(payload: dict) -> tuple[int, str, datetime]:
    payment_method = payload.get("payment_method")
    allowance = payload.get("allowance")
    risk_signals = payload.get("risk_signals")
    metadata = payload.get("metadata")

    if not payment_method:
        raise HTTPException(status_code=400, detail="missing_payment_method")
    if not allowance:
        raise HTTPException(status_code=400, detail="missing_allowance")
    if risk_signals is None:
        raise HTTPException(status_code=400, detail="missing_risk_signals")
    if metadata is None:
        raise HTTPException(status_code=400, detail="missing_metadata")

    max_amount = allowance.get("max_amount")
    currency = allowance.get("currency")
    expires_at = allowance.get("expires_at")

    if max_amount is None or currency is None:
        raise HTTPException(status_code=400, detail="missing_allowance_fields")
    if expires_at is None:
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat().replace("+00:00", "Z")

    return int(max_amount), str(currency), _parse_iso(expires_at)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "psp", "version": "0.3.0"}


@app.post("/agentic_commerce/delegate_payment")
async def delegate_payment(request: Request, response: Response) -> JSONResponse:
    body = await request.body()
    validate_request(request, body)

    payload = await request.json()
    try:
        max_amount, currency, expires_at = _validate_delegate_request(payload)
    except HTTPException as exc:
        return _error(str(exc.detail), "Invalid delegated payment request", status=exc.status_code)

    token_id = f"dpt_{uuid4().hex}"
    record = TokenRecord(
        token_id=token_id,
        max_amount=max_amount,
        currency=currency,
        expires_at=expires_at,
        status="issued",
        created_at=datetime.now(timezone.utc),
        used_at=None,
        metadata=payload.get("metadata", {}),
    )
    save_token(record)

    response_body = {
        "id": token_id,
        "payment_token": token_id,
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "amount": max_amount,
        "currency": currency,
        "status": "issued",
    }

    response.status_code = 200
    return _apply_idempotency(request, body, jsonable_encoder(response_body), status_code=200)


@app.get("/agentic_commerce/delegate_payment/{token_id}")
async def get_delegate_payment(token_id: str, request: Request) -> JSONResponse:
    _ = validate_request(request, b"")
    record = get_token(token_id)
    if not record:
        return _error("token_not_found", "Payment token not found", status=404)
    payload = {
        "id": record.token_id,
        "status": record.status,
        "expires_at": record.expires_at.isoformat().replace("+00:00", "Z"),
        "amount": record.max_amount,
        "currency": record.currency,
    }
    return JSONResponse(content=payload, status_code=200)


@app.post("/agentic_commerce/delegate_payment/{token_id}/redeem")
async def redeem_delegate_payment(token_id: str, request: Request) -> JSONResponse:
    body = await request.body()
    _ = validate_request(request, body)

    record = get_token(token_id)
    if not record:
        return _error("token_not_found", "Payment token not found", status=404)

    if record.status != "issued":
        return _error("token_already_used", "Payment token already redeemed", status=400)

    if datetime.now(timezone.utc) > record.expires_at:
        record.status = "expired"
        save_token(record)
        return _error("token_expired", "Payment token expired", status=400)

    payload = await request.json()
    amount = int(payload.get("amount", 0))
    currency = str(payload.get("currency", ""))

    if amount <= 0 or currency.lower() != record.currency.lower():
        return _error("invalid_allowance", "Allowance currency mismatch", status=400)

    if amount > record.max_amount:
        return _error("allowance_exceeded", "Allowance exceeded", status=400)

    record.status = "redeemed"
    record.used_at = datetime.now(timezone.utc)
    save_token(record)

    response_body = {
        "id": record.token_id,
        "status": "redeemed",
        "amount": amount,
        "currency": currency,
    }
    return JSONResponse(content=response_body, status_code=200)
