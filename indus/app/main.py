from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import logging

from typing import Dict, Any, Optional
from uuid import uuid4

import base64
import hashlib
import hmac

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from .models import (
    IndusCreateCheckoutRequest,
    IndusUpdateCheckoutRequest,
    IndusCheckoutResponse,
    PaymentIntentRequest,
    PaymentIntentResponse,
    UPIReservePayRequest,
    CompleteCheckoutRequest,
    CompleteCheckoutResponse,
    TokenRedeemRequest,
    TokenRedeemResponse,
    AgentCapabilities,
    PaymentHandlerDeclaration,
)
from .merchant_client import MerchantClient
from .razorpay_client import RazorpayClient, RazorpayAPIError
from .sarvam_client import SarvamClient, SarvamAPIError
from .rate_limit import RateLimiter
from .db import init_db, get_db, SessionRecord, PaymentRecord, OrderEvent, TokenRecord, IndusmerchantModel
from .security import validate_merchant_request
from .capabilities import get_indus_capabilities
from .registry import MerchantRecord, MerchantRegisterRequest, MerchantResponse, init_registry


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("indus")

SUPPORTED_API_VERSIONS = {"2026-02-24"}
CURRENT_API_VERSION = "2026-02-24"

app = FastAPI(title="Indus Orchestrator", version="1.0.0")
rate_limiter = RateLimiter()


def _rate_limit_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"{ip}:{request.url.path}"


@app.middleware("http")
async def api_version_middleware(request: Request, call_next):
    requested = request.headers.get("API-Version")
    if requested and requested not in SUPPORTED_API_VERSIONS:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "unsupported_api_version",
                    "message": f"API-Version '{requested}' is not supported. Supported: {sorted(SUPPORTED_API_VERSIONS)}",
                }
            },
        )
    response = await call_next(request)
    response.headers["API-Version"] = CURRENT_API_VERSION
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true":
        result = rate_limiter.check(_rate_limit_key(request))
        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Too many requests"}},
                headers={
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(result.reset_seconds),
                },
            )
    response = await call_next(request)
    return response


def _raise_razorpay_error(exc: RazorpayAPIError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.payload)


def _raise_sarvam_error(exc: SarvamAPIError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.payload)


def _webhook_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _verify_webhook_signature(request: Request, body: bytes) -> None:
    secret = os.getenv("ORDER_WEBHOOK_SECRET")
    if not secret:
        return
    received = request.headers.get("Merchant-Signature")
    if not received:
        raise HTTPException(status_code=401, detail="missing_webhook_signature")
    expected = _webhook_signature(secret, body)
    if not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="invalid_webhook_signature")


def _default_indus_capabilities() -> AgentCapabilities:
    """Capabilities the Indus agent declares when the caller doesn't specify any."""
    return AgentCapabilities(
        payment_methods=["card", "upi_collect", "upi_intent", "upi_qr", "netbanking"],
        payment_handlers=[
            PaymentHandlerDeclaration(
                id="com.razorpay.upi_collect",
                version="2026-02-24",
                psp="razorpay",
                requires_delegate_payment=True,
                requires_pci_compliance=False,
                spec_uri="https://setu.indus.in/spec/2026-02-24/handlers/com.razorpay.upi_collect",
                instrument_schema={
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "description": "UPI Collect payment instrument parameters (Razorpay)",
                    "properties": {
                        "payment_method_type": {
                            "type": "string",
                            "enum": ["upi_collect", "upi_intent", "upi_qr"],
                        },
                        "vpa": {
                            "type": "string",
                            "description": "Virtual Payment Address for upi_collect",
                        },
                    },
                    "if": {"properties": {"payment_method_type": {"const": "upi_collect"}}},
                    "then": {"required": ["vpa"]},
                },
            ),
            PaymentHandlerDeclaration(
                id="com.razorpay.card",
                version="2026-02-24",
                psp="razorpay",
                requires_delegate_payment=True,
                requires_pci_compliance=True,
                spec_uri="https://setu.indus.in/spec/2026-02-24/handlers/com.razorpay.card",
                instrument_schema={
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "description": "Card payment instrument parameters (Razorpay)",
                    "required": ["card_number", "card_exp_month", "card_exp_year", "card_cvc"],
                    "properties": {
                        "card_number":      {"type": "string"},
                        "card_exp_month":   {"type": "string"},
                        "card_exp_year":    {"type": "string"},
                        "card_cvc":         {"type": "string"},
                        "card_holder_name": {"type": "string"},
                        "billing_address":  {"type": "object"},
                    },
                },
            ),
        ],
        extensions=["india_gst", "upi_vpa", "upi_reserve_pay", "discounts"],
        locale="en-IN",
        timezone="Asia/Kolkata",
    )


def _token_ttl_seconds() -> int:
    raw = os.getenv("TOKEN_TTL_SECONDS", "86400")
    try:
        value = int(raw)
    except ValueError:
        value = 86400
    return max(value, 60)


def _issue_token(db, session_id: str, kind: str, payload: Dict[str, Any]) -> str:
    token = f"{kind[:1]}tok_{uuid4().hex}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=_token_ttl_seconds())
    db.merge(
        TokenRecord(
            token=token,
            session_id=session_id,
            kind=kind,
            payload=payload,
            created_at=now,
            expires_at=expires_at,
        )
    )
    return token


@app.on_event("startup")
def _startup() -> None:
    init_db()
    init_registry()
    logger.info("indus_startup")


@app.post("/indus/checkout", response_model=IndusCheckoutResponse)
def create_checkout(payload: IndusCreateCheckoutRequest) -> IndusCheckoutResponse:
    merchant = MerchantClient(payload.merchant_base_url)
    merchant_payload = payload.model_dump(
        exclude={"merchant_base_url", "buyer", "fulfillment_address", "capabilities"},
        exclude_none=True,
    )
    # Declare agent capabilities so merchant can negotiate what both sides support
    caps = payload.capabilities or _default_indus_capabilities()
    merchant_payload["capabilities"] = jsonable_encoder(caps)
    session = merchant.create_checkout_session(merchant_payload)

    session_id = session.get("id")
    if not session_id:
        raise HTTPException(status_code=502, detail="merchant_invalid_response")

    buyer_payload = jsonable_encoder(payload.buyer) if payload.buyer else None
    fulfillment_payload = jsonable_encoder(payload.fulfillment_address) if payload.fulfillment_address else None

    token_update: Dict[str, Any] = {}
    if buyer_payload or fulfillment_payload:
        with get_db() as db:
            if buyer_payload:
                token_update["buyer_token"] = _issue_token(db, session_id, "buyer", buyer_payload)
            if fulfillment_payload:
                token_update["fulfillment_token"] = _issue_token(db, session_id, "fulfillment", fulfillment_payload)
            db.commit()

    if token_update:
        session = merchant.update_checkout_session(session_id, token_update)

    with get_db() as db:
        session_data = dict(session)
        if buyer_payload:
            session_data["indus_buyer"] = buyer_payload
        if fulfillment_payload:
            session_data["indus_fulfillment_address"] = fulfillment_payload
        db.merge(
            SessionRecord(
                session_id=session_id,
                merchant_base_url=payload.merchant_base_url,
                session_data=session_data,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    return IndusCheckoutResponse(merchant_base_url=payload.merchant_base_url, checkout_session=session)


@app.post("/indus/checkout/{session_id}/update", response_model=IndusCheckoutResponse)
def update_checkout(
    session_id: str,
    payload: IndusUpdateCheckoutRequest,
) -> IndusCheckoutResponse:
    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if not record:
            raise HTTPException(status_code=404, detail="unknown_session")
        merchant_base_url = record.merchant_base_url

    merchant = MerchantClient(merchant_base_url)
    payload_data = payload.model_dump(exclude_none=True)
    buyer_payload = payload_data.pop("buyer", None)
    fulfillment_payload = payload_data.pop("fulfillment_address", None)

    token_update: Dict[str, Any] = {}
    if buyer_payload or fulfillment_payload:
        with get_db() as db:
            if buyer_payload:
                token_update["buyer_token"] = _issue_token(db, session_id, "buyer", buyer_payload)
            if fulfillment_payload:
                token_update["fulfillment_token"] = _issue_token(db, session_id, "fulfillment", fulfillment_payload)
            db.commit()
    payload_data.update(token_update)

    session = merchant.update_checkout_session(session_id, payload_data)

    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if record:
            session_data = dict(session)
            existing = record.session_data or {}
            if buyer_payload:
                session_data["indus_buyer"] = buyer_payload
            elif existing.get("indus_buyer"):
                session_data["indus_buyer"] = existing.get("indus_buyer")
            if fulfillment_payload:
                session_data["indus_fulfillment_address"] = fulfillment_payload
            elif existing.get("indus_fulfillment_address"):
                session_data["indus_fulfillment_address"] = existing.get("indus_fulfillment_address")
            record.session_data = session_data
            record.updated_at = datetime.now(timezone.utc)
            db.commit()

    return IndusCheckoutResponse(merchant_base_url=merchant_base_url, checkout_session=session)


@app.get("/indus/checkout/{session_id}", response_model=IndusCheckoutResponse)
def get_checkout(session_id: str) -> IndusCheckoutResponse:
    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if not record:
            raise HTTPException(status_code=404, detail="unknown_session")
        merchant_base_url = record.merchant_base_url

    merchant = MerchantClient(merchant_base_url)
    session = merchant.get_checkout_session(session_id)

    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if record:
            record.session_data = session
            record.updated_at = datetime.now(timezone.utc)
            db.commit()

    return IndusCheckoutResponse(merchant_base_url=merchant_base_url, checkout_session=session)


@app.post("/indus/checkout/{session_id}/cancel", response_model=IndusCheckoutResponse)
def cancel_checkout(session_id: str) -> IndusCheckoutResponse:
    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if not record:
            raise HTTPException(status_code=404, detail="unknown_session")
        merchant_base_url = record.merchant_base_url

    merchant = MerchantClient(merchant_base_url)
    session = merchant.cancel_checkout_session(session_id, {"reason": "user_cancelled"})

    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if record:
            record.session_data = session
            record.updated_at = datetime.now(timezone.utc)
            db.commit()

    return IndusCheckoutResponse(merchant_base_url=merchant_base_url, checkout_session=session)


@app.post("/indus/checkout/{session_id}/payment_intent", response_model=PaymentIntentResponse)
def create_payment_intent(
    session_id: str,
    payload: PaymentIntentRequest,
) -> PaymentIntentResponse:
    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if not record:
            raise HTTPException(status_code=404, detail="unknown_session")

    rzp = RazorpayClient()
    notes: Dict[str, Any] = {"checkout_session_id": session_id}
    if payload.metadata:
        notes.update(payload.metadata)

    try:
        order = rzp.create_order(
            amount=payload.amount,
            currency=payload.currency.upper(),
            receipt=session_id,
            notes=notes,
        )
    except RazorpayAPIError as exc:
        _raise_razorpay_error(exc)

    order_id: str = order["id"]
    payment_method_type = payload.payment_method_type or "upi_collect"
    payment_id: str = ""
    qr_image_url: Optional[str] = None
    upi_deep_link: Optional[str] = None
    status: str = "created"

    try:
        if payment_method_type == "upi_collect":
            upi = payload.upi_data
            if not upi or not upi.vpa:
                raise HTTPException(status_code=400, detail="vpa required for upi_collect")
            customer = payload.customer or {}
            result = rzp.create_upi_payment(
                order_id=order_id,
                vpa=upi.vpa,
                contact=customer.get("phone", ""),
                email=customer.get("email", ""),
                amount=payload.amount,
                currency=payload.currency.upper(),
            )
            payment_id = result.get("razorpay_payment_id") or result.get("payment_id", order_id)
            status = "pending_customer_action"

        elif payment_method_type == "upi_qr":
            import time as _time
            close_by = int(_time.time()) + 900  # 15 min
            result = rzp.create_qr_code(
                name=notes.get("merchant_name", "Indus Merchant"),
                description=f"Order {session_id}",
                amount=payload.amount,
                close_by_unix=close_by,
                notes={"checkout_session_id": session_id},
            )
            payment_id = result.get("id", order_id)
            qr_image_url = result.get("image_url")
            status = "pending_customer_action"

        else:
            # upi_intent — deep link built from order_id + merchant UPI VPA
            payment_id = order_id
            merchant_vpa = ""
            with get_db() as db:
                merch = (
                    db.query(IndusmerchantModel)
                    .filter(IndusmerchantModel.base_url == record.merchant_base_url)
                    .first()
                )
                if merch and merch.upi_vpa:
                    merchant_vpa = merch.upi_vpa
            if not merchant_vpa:
                raise HTTPException(
                    status_code=400,
                    detail="merchant_upi_vpa_not_configured: register the merchant with a upi_vpa to use upi_intent",
                )
            upi_deep_link = (
                f"upi://pay?pa={merchant_vpa}"
                f"&am={payload.amount / 100:.2f}"
                f"&tr={order_id}"
                f"&tn=IndusPayment"
                f"&cu=INR"
            )
            status = "created"

    except RazorpayAPIError as exc:
        _raise_razorpay_error(exc)

    now = datetime.now(timezone.utc)
    with get_db() as db:
        db.merge(
            PaymentRecord(
                payment_id=payment_id,
                order_id=order_id,
                status=status,
                data={
                    "order": order,
                    "payment_method_type": payment_method_type,
                    "metadata": notes,
                },
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()

    return PaymentIntentResponse(
        payment_id=payment_id,
        status=status,
        razorpay_order_id=order_id,
        qr_image_url=qr_image_url,
        upi_deep_link=upi_deep_link,
    )


@app.post("/indus/checkout/{session_id}/reserve_pay")
def create_reserve_pay(
    session_id: str,
    payload: UPIReservePayRequest,
) -> Dict[str, Any]:
    """UPI Reserve Pay (SBMD / PIN-less agentic mandate) — user authorises once,
    agent can debit freely up to max_amount thereafter."""
    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if not record:
            raise HTTPException(status_code=404, detail="unknown_session")

    rzp = RazorpayClient()
    try:
        order = rzp.create_order(
            amount=payload.max_amount,
            currency="INR",
            receipt=f"{session_id}_rp",
            notes={"checkout_session_id": session_id, "type": "reserve_pay"},
        )
        mandate = rzp.create_upi_mandate(
            order_id=order["id"],
            customer_id=payload.customer_id or "",
            vpa=payload.vpa,
            max_amount=payload.max_amount,
            description=payload.description,
        )
    except RazorpayAPIError as exc:
        _raise_razorpay_error(exc)

    return {
        "mandate_payment_id": mandate.get("id"),
        "razorpay_order_id": order["id"],
        "status": mandate.get("status", "created"),
        "vpa": payload.vpa,
        "max_amount": payload.max_amount,
    }


@app.post("/indus/checkout/{session_id}/complete", response_model=CompleteCheckoutResponse)
def complete_checkout(
    session_id: str,
    payload: CompleteCheckoutRequest,
) -> CompleteCheckoutResponse:
    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if not record:
            raise HTTPException(status_code=404, detail="unknown_session")
        merchant_base_url = record.merchant_base_url

    merchant = MerchantClient(merchant_base_url)
    result = merchant.complete_checkout_session(
        session_id,
        payload.model_dump(exclude_none=True),
    )

    order = result.get("order", {})
    return CompleteCheckoutResponse(
        order_id=order.get("id", result.get("order_id", "")),
        status=order.get("status", result.get("status", "unknown")),
        message=result.get("message"),
    )


@app.post("/indus/checkout/{session_id}/refund")
def refund_checkout(
    session_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    """
    Refund a completed checkout session via Razorpay.

    Body (all optional):
      amount   – paise; omit for full refund
      notes    – pass-through metadata
    """
    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if not record:
            raise HTTPException(status_code=404, detail="unknown_session")
        payment_record = (
            db.query(PaymentRecord)
            .filter(PaymentRecord.data["metadata"]["checkout_session_id"].as_string() == session_id)
            .order_by(PaymentRecord.created_at.desc())
            .first()
        )
    if not payment_record:
        raise HTTPException(status_code=404, detail="no_payment_found_for_session")

    rzp = RazorpayClient()
    try:
        return rzp.refund_payment(
            payment_id=payment_record.payment_id,
            amount=payload.get("amount"),
            notes=payload.get("notes"),
        )
    except RazorpayAPIError as exc:
        _raise_razorpay_error(exc)


@app.post("/indus/payments/{payment_id}/refunds")
def razorpay_create_refund(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    """Direct Razorpay refund (when caller already has payment_id)."""
    rzp = RazorpayClient()
    try:
        return rzp.refund_payment(
            payment_id=payment_id,
            amount=payload.get("amount"),
            notes=payload.get("notes"),
        )
    except RazorpayAPIError as exc:
        _raise_razorpay_error(exc)


@app.post("/indus/tokens/{token}/redeem", response_model=TokenRedeemResponse)
def redeem_token(
    token: str,
    request: Request,
    payload: TokenRedeemRequest = Body(default=TokenRedeemRequest()),
) -> TokenRedeemResponse:
    _ = payload  # Reserved for future logging/controls.
    validate_merchant_request(request)
    with get_db() as db:
        record = db.get(TokenRecord, token)
        if not record:
            raise HTTPException(status_code=404, detail="token_not_found")
        if record.expires_at and record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="token_expired")
        return TokenRedeemResponse(
            token=token,
            status="redeemed",
            kind=record.kind,  # type: ignore[arg-type]
            payload=record.payload,
        )


@app.get("/indus/payments/{payment_id}")
def razorpay_retrieve_payment(payment_id: str) -> Dict[str, Any]:
    """Retrieve a Razorpay payment by ID."""
    rzp = RazorpayClient()
    try:
        return rzp.retrieve_payment(payment_id)
    except RazorpayAPIError as exc:
        _raise_razorpay_error(exc)


@app.post("/indus/payments/{payment_id}/capture")
def razorpay_capture_payment(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    """Capture an authorised Razorpay payment."""
    rzp = RazorpayClient()
    try:
        return rzp.capture_payment(
            payment_id=payment_id,
            amount=payload.get("amount", 0),
            currency=payload.get("currency", "INR"),
        )
    except RazorpayAPIError as exc:
        _raise_razorpay_error(exc)


@app.post("/indus/payments/{payment_id}/transfers")
def razorpay_create_transfer(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    """Razorpay Route — split captured payment to a merchant linked account."""
    rzp = RazorpayClient()
    try:
        return rzp.create_transfer(
            payment_id=payment_id,
            account_id=payload["account_id"],
            amount=payload["amount"],
            currency=payload.get("currency", "INR"),
        )
    except RazorpayAPIError as exc:
        _raise_razorpay_error(exc)


@app.post("/indus/sarvam/proxy")
def sarvam_proxy(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        client = SarvamClient()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "sarvam_unavailable", "message": str(exc)}) from exc
    try:
        return client.request(payload)
    except SarvamAPIError as exc:
        _raise_sarvam_error(exc)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "indus", "version": "1.0.0"}


@app.get("/indus/capabilities")
def indus_capabilities() -> dict:
    return get_indus_capabilities()


@app.post("/indus/merchants")
def register_merchant(payload: MerchantRegisterRequest) -> MerchantResponse:
    merchant_id = f"merch_{uuid4().hex}"
    now = datetime.now(timezone.utc)
    record = MerchantRecord(
        id=merchant_id,
        name=payload.name,
        base_url=payload.base_url,
        upi_vpa=payload.upi_vpa,
        razorpay_account_id=payload.razorpay_account_id,
        product_feed_url=payload.product_feed_url,
        created_at=now,
        updated_at=now,
    )
    with get_db() as db:
        db.add(record)
        db.commit()
    return MerchantResponse(
        id=merchant_id,
        name=payload.name,
        base_url=payload.base_url,
        upi_vpa=payload.upi_vpa,
        razorpay_account_id=payload.razorpay_account_id,
        product_feed_url=payload.product_feed_url,
        created_at=now,
    )


@app.get("/indus/merchants")
def list_merchants() -> list:
    with get_db() as db:
        records = db.query(MerchantRecord).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "base_url": r.base_url,
                "upi_vpa": r.upi_vpa,
                "razorpay_account_id": r.razorpay_account_id,
                "product_feed_url": r.product_feed_url,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]


@app.get("/indus/merchants/{merchant_id}")
def get_merchant(merchant_id: str) -> dict:
    with get_db() as db:
        record = db.get(MerchantRecord, merchant_id)
        if not record:
            raise HTTPException(status_code=404, detail={"code": "merchant_not_found", "message": "Merchant not found"})
        return {
            "id": record.id,
            "name": record.name,
            "base_url": record.base_url,
            "upi_vpa": record.upi_vpa,
            "razorpay_account_id": record.razorpay_account_id,
            "product_feed_url": record.product_feed_url,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }


@app.post("/indus/sarvam/product_search")
def sarvam_product_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multilingual product search powered by Sarvam-M.
    Fetches the merchant's real product feed, passes it as context, and asks
    Sarvam-M to find matching items in the buyer's language.
    """
    query = payload.get("query", "")
    language = payload.get("language", "en")
    merchant_base_url = payload.get("merchant_base_url", "")

    if not query:
        raise HTTPException(status_code=400, detail={"code": "missing_query", "message": "query is required"})
    if not merchant_base_url:
        raise HTTPException(status_code=400, detail={"code": "missing_merchant_url", "message": "merchant_base_url is required"})

    # Fetch real product catalog from merchant feed
    try:
        merchant = MerchantClient(merchant_base_url)
        feed = merchant.get_product_feed()
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"code": "merchant_feed_unavailable", "message": str(exc)}) from exc

    items = feed.get("items", [])[:50]  # cap at 50 to stay within context
    product_lines = "\n".join(
        f"id:{item['id']} | {item['title']} | ₹{item.get('price_paise', 0) // 100} | {item.get('description', '')}"
        for item in items
        if item.get("availability") == "in_stock"
    )

    try:
        client = SarvamClient()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "sarvam_unavailable", "message": str(exc)}) from exc

    messages = [
        {
            "role": "system",
            "content": (
                "You are a product search assistant for an Indian e-commerce store. "
                "Given the product catalog below, find items that best match the user's query. "
                "Respond ONLY with a valid JSON object (no markdown, no extra text) in this exact format:\n"
                '{"matches": [{"id": "item_id", "title": "...", "price_paise": 0, "reason": "why it matches"}], '
                '"message": "brief response to the buyer in their requested language"}\n\n'
                f"CATALOG:\n{product_lines}"
            ),
        },
        {"role": "user", "content": f"Language: {language}\nQuery: {query}"},
    ]

    try:
        result = client.chat(messages, temperature=0.2, max_tokens=512)
    except SarvamAPIError as exc:
        _raise_sarvam_error(exc)

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    try:
        import json as _json
        parsed = _json.loads(content)
    except (ValueError, KeyError):
        parsed = {"matches": [], "message": content}

    return {
        "query": query,
        "language": language,
        "merchant_base_url": merchant_base_url,
        **parsed,
    }


@app.post("/indus/sarvam/checkout_assist")
def sarvam_checkout_assist(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Multilingual checkout assistant powered by Sarvam-M.
    Loads the real session state (items, totals, fulfillment options) from DB
    and passes it as context so Sarvam-M can give grounded, actionable responses.
    """
    session_id = payload.get("session_id", "")
    user_message = payload.get("user_message", "")
    language = payload.get("language", "hi")

    if not user_message:
        raise HTTPException(status_code=400, detail={"code": "missing_message", "message": "user_message is required"})

    # Load session context from DB so the assistant knows what's in the cart
    session_context = ""
    if session_id:
        with get_db() as db:
            record = db.query(SessionRecord).filter(SessionRecord.session_id == session_id).first()
        if record:
            data = record.session_data or {}
            status = data.get("status", "unknown")
            totals = data.get("totals", {})
            line_items = data.get("line_items", [])
            fulfillment_opts = data.get("fulfillment_options", [])

            item_lines = "\n".join(
                f"  - {i.get('title', i.get('product_id', 'item'))} x{i.get('quantity', 1)}"
                f" @ ₹{i.get('unit_price', 0) // 100}"
                for i in line_items
            )
            opt_lines = "\n".join(
                f"  - {o['id']}: {o.get('title', '')} ₹{o.get('total', 0) // 100}"
                for o in fulfillment_opts
            )
            session_context = (
                f"\n\nSESSION CONTEXT ({session_id}):"
                f"\nStatus: {status}"
                f"\nTotal: ₹{totals.get('total', 0) // 100}"
                f"\nItems:\n{item_lines or '  (none)'}"
                f"\nFulfillment options:\n{opt_lines or '  (none yet)'}"
            )

    try:
        client = SarvamClient()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "sarvam_unavailable", "message": str(exc)}) from exc

    messages = [
        {
            "role": "system",
            "content": (
                "You are a checkout assistant helping an Indian shopper complete their purchase via the Setu protocol. "
                "Help the buyer select a shipping option, understand their order total, apply a coupon, or confirm their address. "
                "Respond ONLY with a valid JSON object (no markdown, no extra text):\n"
                '{"message": "response in the buyer\'s language", '
                '"suggested_action": null | {"action": "select_fulfillment", "fulfillment_option_id": "..."} | '
                '{"action": "apply_coupon", "coupon_code": "..."} | {"action": "confirm_order"}}'
                + session_context
            ),
        },
        {"role": "user", "content": f"Language: {language}\n{user_message}"},
    ]

    try:
        result = client.chat(messages, temperature=0.3, max_tokens=512)
    except SarvamAPIError as exc:
        _raise_sarvam_error(exc)

    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
    try:
        import json as _json
        parsed = _json.loads(content)
    except (ValueError, KeyError):
        parsed = {"message": content, "suggested_action": None}

    return {
        "session_id": session_id,
        "language": language,
        **parsed,
    }


@app.post("/webhooks/orders")
async def order_webhook(request: Request) -> dict:
    body = await request.body()
    _verify_webhook_signature(request, body)
    payload = jsonable_encoder(await request.json())
    with get_db() as db:
        db.add(OrderEvent(payload=jsonable_encoder(payload)))
        db.commit()
    return {"status": "received"}
