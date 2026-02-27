from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .catalog import get_item
from .discounts import apply_coupon, get_coupon
from .feed import build_product_feed, render_product_feed
from .db import init_db, get_db, CheckoutSessionModel, OrderModel
from .idempotency import IdempotencyStore, IdempotencyRecord
from .models import (
    CheckoutSessionCreateRequest,
    CheckoutSessionUpdateRequest,
    CheckoutSessionCompleteRequest,
    CancelSessionRequest,
    CheckoutSession,
    CheckoutLineItem,
    CheckoutItem,
    TotalsEntry,
    FulfillmentOption,
    Message,
    InfoMessage,
    WarningMessage,
    ErrorMessage,
    OrderSummary,
    ItemInput,
    PaymentProvider,
    Link,
    AgentCapabilities,
    PaymentHandlerDeclaration,
    NegotiatedCapabilities,
)
from .payment_verify import verify_hyperswitch_payment
from .indus_client import IndusClient, IndusClientError
from .security import validate_request
from .webhooks import send_order_event
from .rate_limit import RateLimiter
from .audit import log_event


TAX_RATE = 0.18


FULFILLMENT_OPTION_TEMPLATES = [
    {
        "id": "standard",
        "title": "Standard Delivery",
        "subtitle": "3-5 business days",
        "carrier": "Partner Logistics",
        "amount": 0,
        "min_days": 3,
        "max_days": 5,
    },
    {
        "id": "express",
        "title": "Express Delivery",
        "subtitle": "1-2 business days",
        "carrier": "Partner Logistics",
        "amount": 4900,
        "min_days": 1,
        "max_days": 2,
    },
]

SUPPORTED_PAYMENT_METHODS = ["card", "upi"]

# ---------------------------------------------------------------------------
# Capability negotiation
# ---------------------------------------------------------------------------

_MERCHANT_PAYMENT_METHODS: set = {"card", "upi", "upi_collect", "upi_intent", "upi_qr"}

_MERCHANT_HANDLERS: List[PaymentHandlerDeclaration] = [
    PaymentHandlerDeclaration(
        id="com.hyperswitch.upi",
        version="2026-02-24",
        psp="hyperswitch",
        requires_delegate_payment=True,
        requires_pci_compliance=False,
    ),
    PaymentHandlerDeclaration(
        id="com.hyperswitch.card",
        version="2026-02-24",
        psp="hyperswitch",
        requires_delegate_payment=True,
        requires_pci_compliance=True,
    ),
]

_MERCHANT_EXTENSIONS: set = {"india_gst", "upi_vpa", "discounts"}


def _negotiate_capabilities(agent: Optional[AgentCapabilities]) -> NegotiatedCapabilities:
    """Intersect what the agent declared with what this merchant supports.
    If agent sends no capabilities, return full merchant capabilities.
    """
    if agent is None or (not agent.payment_methods and not agent.payment_handlers and not agent.extensions):
        return NegotiatedCapabilities(
            payment_methods=sorted(_MERCHANT_PAYMENT_METHODS),
            payment_handlers=_MERCHANT_HANDLERS,
            extensions=sorted(_MERCHANT_EXTENSIONS),
        )

    # Intersect payment methods; fall back to all merchant methods if no overlap
    agreed_methods = sorted(set(agent.payment_methods) & _MERCHANT_PAYMENT_METHODS)
    if not agreed_methods:
        agreed_methods = sorted(_MERCHANT_PAYMENT_METHODS)

    # Intersect handlers by ID; fall back to all merchant handlers if no overlap
    agent_ids = {h.id for h in agent.payment_handlers}
    agreed_handlers = [h for h in _MERCHANT_HANDLERS if h.id in agent_ids]
    if not agreed_handlers:
        agreed_handlers = _MERCHANT_HANDLERS

    # Intersect extensions; fall back to all merchant extensions if no overlap
    agreed_extensions = sorted(set(agent.extensions) & _MERCHANT_EXTENSIONS)
    if not agreed_extensions:
        agreed_extensions = sorted(_MERCHANT_EXTENSIONS)

    return NegotiatedCapabilities(
        payment_methods=agreed_methods,
        payment_handlers=agreed_handlers,
        extensions=agreed_extensions,
        locale=agent.locale,
        timezone=agent.timezone,
    )


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("merchant")

app = FastAPI(title="Merchant API", version="1.0.0")
rate_limiter = RateLimiter()


def _rate_limit_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"{ip}:{request.url.path}"


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


@app.on_event("startup")
def _startup() -> None:
    init_db()
    logger.info("merchant_startup")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": exc.detail}
    payload = {
        "error": {
            "code": detail.get("code", "request_error"),
            "message": detail.get("message", detail.get("detail", str(detail))),
            "field": detail.get("field"),
        }
    }
    return JSONResponse(content=payload, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    payload = {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed",
        }
    }
    return JSONResponse(content=payload, status_code=422)


def _build_line_items(items: List[ItemInput], coupon_code: str | None = None) -> List[CheckoutLineItem]:
    from .models import GSTMetadata
    line_items: List[CheckoutLineItem] = []
    for item in items:
        catalog_item = get_item(item.id)
        base_amount = catalog_item["price"] * item.quantity
        discount = apply_coupon(coupon_code or "", base_amount) if coupon_code else 0
        subtotal = base_amount - discount
        tax = int(round(subtotal * TAX_RATE))
        total = subtotal + tax
        hsn_code = catalog_item.get("hsn_code")
        gst_meta = GSTMetadata(hsn_code=hsn_code) if hsn_code else None
        line_items.append(
            CheckoutLineItem(
                id=f"li_{uuid4().hex}",
                item=CheckoutItem(
                    id=item.id,
                    quantity=item.quantity,
                    title=catalog_item.get("title"),
                    image_url=catalog_item.get("image_url"),
                ),
                base_amount=base_amount,
                discount=discount,
                subtotal=subtotal,
                tax=tax,
                total=total,
                gst_metadata=gst_meta,
            )
        )
    return line_items


def _compute_totals(line_items: List[CheckoutLineItem], shipping_amount: int) -> List[TotalsEntry]:
    items_base = sum(li.base_amount for li in line_items)
    tax = sum(li.tax for li in line_items)
    items_discount = sum(li.discount for li in line_items)
    subtotal = items_base - items_discount
    total = subtotal + tax + shipping_amount
    return [
        TotalsEntry(type="items_base_amount", display_text="Items subtotal", amount=items_base),
        TotalsEntry(type="items_discount", display_text="Items discount", amount=items_discount),
        TotalsEntry(type="subtotal", display_text="Subtotal", amount=subtotal),
        TotalsEntry(type="tax", display_text="Tax", amount=tax),
        TotalsEntry(type="fulfillment", display_text="Shipping", amount=shipping_amount),
        TotalsEntry(type="total", display_text="Total", amount=total),
    ]


def _get_shipping_amount(fulfillment_option_id: str | None) -> int:
    if not fulfillment_option_id:
        return 0
    for option in FULFILLMENT_OPTION_TEMPLATES:
        if option["id"] == fulfillment_option_id:
            return int(option["amount"])
    return 0


def _is_valid_fulfillment_option(option_id: str) -> bool:
    return any(option["id"] == option_id for option in FULFILLMENT_OPTION_TEMPLATES)


def _build_fulfillment_options() -> List[FulfillmentOption]:
    now = datetime.now(timezone.utc)
    options: List[FulfillmentOption] = []
    for option in FULFILLMENT_OPTION_TEMPLATES:
        earliest = now + timedelta(days=int(option["min_days"]))
        latest = now + timedelta(days=int(option["max_days"]))
        subtotal = int(option["amount"])
        tax = 0
        total = subtotal + tax
        options.append(
            FulfillmentOption(
                type="shipping",
                id=option["id"],
                title=option["title"],
                subtitle=option["subtitle"],
                carrier=option["carrier"],
                earliest_delivery_time=earliest,
                latest_delivery_time=latest,
                subtotal=subtotal,
                tax=tax,
                total=total,
            )
        )
    return options


def _build_links() -> List[Link]:
    links: List[Link] = []
    privacy = os.getenv("MERCHANT_PRIVACY_URL")
    tos = os.getenv("MERCHANT_TOS_URL")
    support = os.getenv("MERCHANT_SUPPORT_URL")
    if privacy:
        links.append(Link(type="privacy_policy", url=privacy))
    if tos:
        links.append(Link(type="terms_of_use", url=tos))
    if support:
        links.append(Link(type="support", url=support))
    return links


def _payment_provider() -> PaymentProvider:
    return PaymentProvider(provider="hyperswitch", supported_payment_methods=SUPPORTED_PAYMENT_METHODS)


def _extract_items_from_session(session: Dict[str, Any]) -> List[ItemInput]:
    items: List[ItemInput] = []
    for line_item in session.get("line_items", []):
        item_data = line_item.get("item", {})
        items.append(ItemInput(id=item_data.get("id"), quantity=item_data.get("quantity", 1)))
    return items


def _apply_idempotency(
    request: Request,
    response: Response,
    body: bytes,
    payload: Dict[str, Any],
    status_code: int,
    store: IdempotencyStore,
) -> JSONResponse:
    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        response.status_code = status_code
        return JSONResponse(content=payload, status_code=status_code)

    request_hash = store.build_request_hash(request.method, request.url.path, body)
    existing = store.get(idem_key)
    if existing:
        if existing.request_hash != request_hash:
            raise HTTPException(status_code=409, detail={"code": "request_not_idempotent", "message": "Idempotency key conflict"})
        return JSONResponse(content=existing.response_body, status_code=existing.status_code)

    store.save(idem_key, IdempotencyRecord(request_hash, payload, status_code))
    response.status_code = status_code
    return JSONResponse(content=payload, status_code=status_code)


def _set_common_headers(request: Request, response: Response) -> None:
    if request.headers.get("Idempotency-Key"):
        response.headers["Idempotency-Key"] = request.headers.get("Idempotency-Key")
    request_id = request.headers.get("X-Request-Id")
    if request_id:
        response.headers["X-Request-Id"] = request_id


def _session_ttl_hours() -> int:
    return int(os.getenv("SESSION_TTL_HOURS", "24"))


def _session_expires_at(now: datetime) -> datetime:
    return now + timedelta(hours=_session_ttl_hours())


def _is_session_expired(session_data: Dict[str, Any]) -> bool:
    expires_at_str = session_data.get("expires_at")
    if not expires_at_str:
        return False
    try:
        expires_at = datetime.fromisoformat(str(expires_at_str).replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expires_at
    except ValueError:
        return False


def _status_for_session(fulfillment_token: str | None, fulfillment_option_id: str | None) -> str:
    if not fulfillment_token:
        return "not_ready_for_payment"
    if not fulfillment_option_id:
        return "not_ready_for_payment"
    return "ready_for_payment"


def _messages_for_status(
    fulfillment_token: str | None,
    fulfillment_option_id: str | None,
    *,
    coupon_invalid: bool = False,
    out_of_stock_item: str | None = None,
    requires_3ds: bool = False,
    low_stock_item: str | None = None,
) -> List[Message]:
    msgs: List[Message] = []

    # Errors — highest priority
    if out_of_stock_item:
        msgs.append(
            ErrorMessage(
                code="out_of_stock",
                severity="high",
                content=f"'{out_of_stock_item}' is out of stock",
                param="items",
            )
        )
    if coupon_invalid:
        msgs.append(
            ErrorMessage(
                code="coupon_invalid",
                severity="medium",
                content="The coupon code you entered is not valid",
                param="coupon_code",
            )
        )
    if requires_3ds:
        msgs.append(
            ErrorMessage(
                code="requires_3ds",
                severity="high",
                content="3D Secure authentication is required to complete payment",
                param="payment_data.token",
            )
        )

    # Warnings — informational, non-blocking
    if low_stock_item:
        msgs.append(
            WarningMessage(
                code="low_stock",
                severity="low",
                content=f"Only a few units of '{low_stock_item}' remain",
                param="items",
            )
        )

    # Info — guidance messages for incomplete sessions
    if not fulfillment_token:
        msgs.append(
            InfoMessage(
                content="Provide a fulfillment address to proceed",
                param="fulfillment_address",
            )
        )
    elif not fulfillment_option_id:
        msgs.append(
            InfoMessage(
                content="Select a fulfillment option to proceed",
                param="fulfillment_option_id",
            )
        )

    return msgs


def _redeem_token(token: str, expected_kind: str) -> Dict[str, Any]:
    try:
        client = IndusClient()
        data = client.redeem_token(token, purpose="checkout")
    except IndusClientError as exc:
        payload = exc.payload if isinstance(exc.payload, dict) else {"message": "Indus token redeem failed"}
        raise HTTPException(status_code=exc.status_code, detail=payload) from exc

    if data.get("kind") != expected_kind:
        raise HTTPException(
            status_code=400,
            detail={"code": "token_kind_mismatch", "message": "Token type does not match expected data"},
        )
    return data.get("payload", {})


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "merchant", "version": "1.0.0"}


@app.get("/capabilities")
def capabilities() -> dict:
    return {
        "supported_payment_methods": ["card", "upi"],
        "fulfillment_types": ["shipping"],
        "currency": "inr",
        "country": "IN",
    }


@app.post("/checkout_sessions")
async def create_checkout_session(
    request: Request,
    response: Response,
) -> JSONResponse:
    body = await request.body()
    validate_request(request, body)

    payload = CheckoutSessionCreateRequest.model_validate_json(body)
    try:
        _ = [_ for _ in (get_item(item.id) for item in payload.items)]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail={"code": "unknown_item", "message": str(exc)}) from exc

    line_items = _build_line_items(payload.items)
    totals = _compute_totals(line_items, shipping_amount=0)

    if payload.fulfillment_token:
        _redeem_token(payload.fulfillment_token, "fulfillment")
    if payload.buyer_token:
        _redeem_token(payload.buyer_token, "buyer")

    fulfillment_token = payload.fulfillment_token
    status = _status_for_session(fulfillment_token, None)
    now = datetime.now(timezone.utc)
    session = CheckoutSession(
        id=f"cs_{uuid4().hex}",
        status=status,
        currency="inr",
        expires_at=_session_expires_at(now),
        buyer_token=payload.buyer_token,
        fulfillment_token=fulfillment_token,
        line_items=line_items,
        totals=totals,
        fulfillment_options=_build_fulfillment_options(),
        fulfillment_option_id=None,
        payment_provider=_payment_provider(),
        messages=_messages_for_status(fulfillment_token, None),
        links=_build_links(),
        created_at=now,
        updated_at=now,
        negotiated_capabilities=_negotiate_capabilities(payload.capabilities),
    )

    with get_db() as db:
        db.merge(
            CheckoutSessionModel(
                id=session.id,
                status=session.status,
                currency=session.currency,
                data=jsonable_encoder(session),
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
        )
        db.commit()
        store = IdempotencyStore(db)
        _set_common_headers(request, response)
        return _apply_idempotency(
            request,
            response,
            body,
            jsonable_encoder(session),
            status_code=201,
            store=store,
        )


@app.post("/checkout_sessions/{session_id}")
async def update_checkout_session(
    session_id: str,
    request: Request,
    response: Response,
) -> JSONResponse:
    body = await request.body()
    validate_request(request, body)

    with get_db() as db:
        row = db.get(CheckoutSessionModel, session_id)
        if not row:
            raise HTTPException(status_code=404, detail={"code": "checkout_session_not_found", "message": "Checkout session not found"})
        store = IdempotencyStore(db)

        session_data: Dict[str, Any] = dict(row.data)

        if _is_session_expired(session_data):
            raise HTTPException(status_code=409, detail={"code": "checkout_session_expired", "message": "Checkout session has expired"})

        payload = CheckoutSessionUpdateRequest.model_validate_json(body)

        items = _extract_items_from_session(session_data)
        if payload.items is not None:
            items = payload.items

        if payload.buyer_token is not None:
            _redeem_token(payload.buyer_token, "buyer")
            session_data["buyer_token"] = payload.buyer_token
        if payload.fulfillment_token is not None:
            _redeem_token(payload.fulfillment_token, "fulfillment")
            session_data["fulfillment_token"] = payload.fulfillment_token
        session_data.pop("buyer", None)
        session_data.pop("fulfillment_address", None)
        if payload.fulfillment_option_id is not None:
            if not _is_valid_fulfillment_option(payload.fulfillment_option_id):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "invalid_fulfillment_option",
                        "message": "Fulfillment option is invalid",
                        "field": "fulfillment_option_id",
                    },
                )
            session_data["fulfillment_option_id"] = payload.fulfillment_option_id

        if payload.coupon_code is not None:
            if payload.coupon_code and not get_coupon(payload.coupon_code):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "invalid_coupon",
                        "message": "Coupon code is invalid",
                        "field": "coupon_code",
                    },
                )
            session_data["coupon_code"] = payload.coupon_code or None

        coupon_code = session_data.get("coupon_code")
        line_items = _build_line_items(items, coupon_code=coupon_code)
        fulfillment_option_id = session_data.get("fulfillment_option_id")
        shipping_amount = _get_shipping_amount(fulfillment_option_id)
        totals = _compute_totals(line_items, shipping_amount=shipping_amount)

        status = _status_for_session(
            session_data.get("fulfillment_token"),
            session_data.get("fulfillment_option_id"),
        )
        now = datetime.now(timezone.utc)
        session_data.update(
            {
                "line_items": jsonable_encoder(line_items),
                "totals": jsonable_encoder(totals),
                "fulfillment_options": jsonable_encoder(_build_fulfillment_options()),
                "payment_provider": jsonable_encoder(_payment_provider()),
                "links": jsonable_encoder(_build_links()),
                "updated_at": now.isoformat(),
                "status": status,
                "messages": jsonable_encoder(
                    _messages_for_status(
                        session_data.get("fulfillment_token"),
                        session_data.get("fulfillment_option_id"),
                    )
                ),
            }
        )

        row.status = session_data.get("status", row.status)
        row.updated_at = now
        row.data = session_data
        db.commit()

        _set_common_headers(request, response)
        return _apply_idempotency(
            request,
            response,
            body,
            session_data,
            status_code=200,
            store=store,
        )


@app.get("/checkout_sessions/{session_id}")
async def get_checkout_session(
    session_id: str,
    request: Request,
    response: Response,
) -> JSONResponse:
    body = await request.body()
    validate_request(request, body)

    with get_db() as db:
        row = db.get(CheckoutSessionModel, session_id)
        if not row:
            raise HTTPException(status_code=404, detail={"code": "checkout_session_not_found", "message": "Checkout session not found"})
        session_data = dict(row.data)

    # Surface expired status dynamically without mutating DB — terminal states keep their state
    if _is_session_expired(session_data) and session_data.get("status") not in {"completed", "canceled", "expired"}:
        session_data["status"] = "expired"

    _set_common_headers(request, response)
    return JSONResponse(content=session_data, status_code=200)


@app.post("/checkout_sessions/{session_id}/cancel")
async def cancel_checkout_session(
    session_id: str,
    request: Request,
    response: Response,
) -> JSONResponse:
    body = await request.body()
    validate_request(request, body)

    with get_db() as db:
        row = db.get(CheckoutSessionModel, session_id)
        if not row:
            raise HTTPException(status_code=404, detail={"code": "checkout_session_not_found", "message": "Checkout session not found"})
        store = IdempotencyStore(db)

        _ = CancelSessionRequest.model_validate_json(body) if body else None
        session_data: Dict[str, Any] = dict(row.data)

        terminal = {"completed", "canceled", "expired"}
        if session_data.get("status") in terminal or _is_session_expired(session_data):
            raise HTTPException(status_code=405, detail={"code": "checkout_session_not_cancelable", "message": "Checkout session cannot be canceled"})

        now = datetime.now(timezone.utc)
        session_data["status"] = "canceled"
        session_data["updated_at"] = now.isoformat()

        row.status = "canceled"
        row.updated_at = now
        row.data = session_data
        db.commit()

        _set_common_headers(request, response)
        return _apply_idempotency(
            request,
            response,
            body,
            session_data,
            status_code=200,
            store=store,
        )


@app.post("/checkout_sessions/{session_id}/complete")
async def complete_checkout_session(
    session_id: str,
    request: Request,
    response: Response,
) -> JSONResponse:
    body = await request.body()
    validate_request(request, body)

    with get_db() as db:
        row = db.get(CheckoutSessionModel, session_id)
        if not row:
            raise HTTPException(status_code=404, detail={"code": "checkout_session_not_found", "message": "Checkout session not found"})
        store = IdempotencyStore(db)

        session_data: Dict[str, Any] = dict(row.data)
        payload = CheckoutSessionCompleteRequest.model_validate_json(body)

        if _is_session_expired(session_data):
            raise HTTPException(status_code=409, detail={"code": "checkout_session_expired", "message": "Checkout session has expired"})

        if session_data.get("status") != "ready_for_payment":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "checkout_session_not_ready",
                    "message": "Checkout session is not ready for payment",
                },
            )

        totals = session_data.get("totals", [])
        total_amount = next((t.get("amount") for t in totals if t.get("type") == "total"), None)
        if total_amount is None:
            raise HTTPException(status_code=500, detail={"code": "totals_missing", "message": "Totals missing"})

        buyer: Dict[str, Any] | None = None
        fulfillment_address: Dict[str, Any] | None = None
        buyer_token = session_data.get("buyer_token")
        fulfillment_token = session_data.get("fulfillment_token")
        if buyer_token:
            buyer = _redeem_token(buyer_token, "buyer")
        if fulfillment_token:
            fulfillment_address = _redeem_token(fulfillment_token, "fulfillment")
        if not fulfillment_address:
            raise HTTPException(
                status_code=409,
                detail={"code": "fulfillment_missing", "message": "Fulfillment address missing"},
            )

        payment = payload.payment_data
        payment_currency = session_data.get("currency")

        if payment.provider != "hyperswitch":
            raise HTTPException(
                status_code=400,
                detail={"code": "unsupported_payment_provider", "message": "Unsupported payment provider"},
            )

        token = payment.token
        if not token:
            raise HTTPException(status_code=400, detail={"code": "missing_payment_token", "message": "Missing payment token"})

        # pending_approval: merchant must review before charging (B2B / high-value orders)
        if payment.approval_required:
            now = datetime.now(timezone.utc)
            session_data["status"] = "pending_approval"
            session_data["updated_at"] = now.isoformat()
            session_data["messages"] = jsonable_encoder([
                InfoMessage(
                    severity="medium",
                    content="Your order is awaiting merchant approval before payment is collected",
                )
            ])
            row.status = "pending_approval"
            row.updated_at = now
            row.data = session_data
            db.commit()
            return _apply_idempotency(request, body, session_data, status_code=200, store=store)

        verified, reason = verify_hyperswitch_payment(
            payment_id=token,
            amount=int(total_amount),
            currency=payment_currency or "",
        )
        if not verified:
            if reason == "requires_3ds":
                now = datetime.now(timezone.utc)
                session_data["status"] = "authentication_required"
                session_data["updated_at"] = now.isoformat()
                session_data["messages"] = jsonable_encoder(
                    _messages_for_status(
                        session_data.get("fulfillment_token"),
                        session_data.get("fulfillment_option_id"),
                        requires_3ds=True,
                    )
                )
                row.status = "authentication_required"
                row.updated_at = now
                row.data = session_data
                db.commit()
                return _apply_idempotency(request, body, session_data, status_code=200, store=store)
            raise HTTPException(status_code=400, detail={"code": "payment_not_verified", "message": f"Payment not verified: {reason}"})

        log_event(
            db,
            "payment_verified",
            session_id,
            {
                "payment_id": token,
                "amount": int(total_amount),
                "currency": payment_currency,
                "status": "verified",
            },
        )

        now = datetime.now(timezone.utc)
        order_id = f"ord_{uuid4().hex}"
        order = OrderSummary(
            id=order_id,
            status="created",
            created_at=now,
        )

        session_data["status"] = "completed"
        if buyer:
            session_data["buyer"] = buyer
        if fulfillment_address:
            session_data["fulfillment_address"] = fulfillment_address
        session_data["order"] = jsonable_encoder(order)
        session_data["updated_at"] = now.isoformat()

        row.status = "completed"
        row.updated_at = now
        row.data = session_data
        db.merge(
            OrderModel(
                id=order_id,
                checkout_session_id=session_id,
                status="created",
                data=session_data["order"],
                created_at=now,
                updated_at=now,
            )
        )
        log_event(
            db,
            "order_created",
            order_id,
            {
                "checkout_session_id": session_id,
                "status": "created",
                "total_amount": total_amount,
                "currency": session_data.get("currency"),
            },
        )
        db.commit()

        send_order_event(
            "order.created",
            {
                "order_id": order_id,
                "checkout_session_id": session_id,
                "status": "created",
                "total_amount": total_amount,
                "currency": session_data.get("currency"),
            },
        )

        order_response = {
            "id": session_id,
            "status": "completed",
            "order": jsonable_encoder(order),
        }
        _set_common_headers(request, response)
        return _apply_idempotency(
            request,
            response,
            body,
            order_response,
            status_code=201,
            store=store,
        )


@app.post("/orders/{order_id}/update")
async def update_order(
    order_id: str,
    request: Request,
) -> JSONResponse:
    body = await request.body()
    validate_request(request, body)
    payload = await request.json()
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail={"code": "missing_status", "message": "Missing status"})

    with get_db() as db:
        order_row = db.get(OrderModel, order_id)
        if not order_row:
            raise HTTPException(status_code=404, detail={"code": "order_not_found", "message": "Order not found"})

        order_data = dict(order_row.data)
        order_data["status"] = new_status
        now = datetime.now(timezone.utc)
        order_data["updated_at"] = now.isoformat()

        order_row.status = new_status
        order_row.data = order_data
        order_row.updated_at = now
        db.commit()

    send_order_event(
        "order.updated",
        {
            "order_id": order_id,
            "status": new_status,
        },
    )

    return JSONResponse(content=order_data, status_code=200)


@app.get("/product_feed")
async def get_product_feed(
    request: Request,
    response: Response,
) -> JSONResponse:
    body = await request.body()
    validate_request(request, body)

    format_param = request.query_params.get("format", "json")
    if format_param == "csv":
        content = render_product_feed(format="csv")
        _set_common_headers(request, response)
        return Response(content=content, media_type="text/csv")

    feed = build_product_feed(currency="inr")
    _set_common_headers(request, response)
    return JSONResponse(content=feed, status_code=200)
