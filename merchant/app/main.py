from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .catalog import get_item
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
    OrderSummary,
    ItemInput,
    PaymentProvider,
    Link,
)
from .payment_verify import verify_hyperswitch_payment
from .security import validate_request
from .webhooks import send_order_event


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


app = FastAPI(title="Merchant API", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()


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


def _build_line_items(items: List[ItemInput]) -> List[CheckoutLineItem]:
    line_items: List[CheckoutLineItem] = []
    for item in items:
        catalog_item = get_item(item.id)
        base_amount = catalog_item["price"] * item.quantity
        discount = 0
        subtotal = base_amount - discount
        tax = int(round(subtotal * TAX_RATE))
        total = subtotal + tax
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


def _status_for_session(fulfillment_address: Dict[str, Any] | None, fulfillment_option_id: str | None) -> str:
    if not fulfillment_address:
        return "not_ready_for_payment"
    if not fulfillment_option_id:
        return "not_ready_for_payment"
    return "ready_for_payment"


def _messages_for_status(
    fulfillment_address: Dict[str, Any] | None,
    fulfillment_option_id: str | None,
) -> List[Message]:
    if not fulfillment_address:
        return [
            Message(
                type="info",
                content_type="text",
                content="Fulfillment address required",
                param="fulfillment_address",
            )
        ]
    if not fulfillment_option_id:
        return [
            Message(
                type="info",
                content_type="text",
                content="Select a fulfillment option",
                param="fulfillment_option_id",
            )
        ]
    return []


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

    fulfillment_address = jsonable_encoder(payload.fulfillment_address) if payload.fulfillment_address else None
    status = _status_for_session(fulfillment_address, None)
    now = datetime.now(timezone.utc)
    session = CheckoutSession(
        id=f"cs_{uuid4().hex}",
        status=status,
        currency="inr",
        buyer=payload.buyer,
        fulfillment_address=payload.fulfillment_address,
        line_items=line_items,
        totals=totals,
        fulfillment_options=_build_fulfillment_options(),
        fulfillment_option_id=None,
        payment_provider=_payment_provider(),
        messages=_messages_for_status(fulfillment_address, None),
        links=_build_links(),
        created_at=now,
        updated_at=now,
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
        payload = CheckoutSessionUpdateRequest.model_validate_json(body)

        items = _extract_items_from_session(session_data)
        if payload.items is not None:
            items = payload.items

        if payload.buyer is not None:
            session_data["buyer"] = jsonable_encoder(payload.buyer)
        if payload.fulfillment_address is not None:
            session_data["fulfillment_address"] = jsonable_encoder(payload.fulfillment_address)
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

        line_items = _build_line_items(items)
        fulfillment_option_id = session_data.get("fulfillment_option_id")
        shipping_amount = _get_shipping_amount(fulfillment_option_id)
        totals = _compute_totals(line_items, shipping_amount=shipping_amount)

        status = _status_for_session(
            session_data.get("fulfillment_address"),
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
                        session_data.get("fulfillment_address"),
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
        session_data = row.data

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

        if session_data.get("status") in {"completed", "canceled"}:
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

        payment = payload.payment_data
        payment_currency = session_data.get("currency")

        if int(payment_amount) != int(total_amount):
            raise HTTPException(status_code=400, detail={"code": "payment_amount_mismatch", "message": "Payment amount mismatch"})

        if payment.provider != "hyperswitch":
            raise HTTPException(
                status_code=400,
                detail={"code": "unsupported_payment_provider", "message": "Unsupported payment provider"},
            )

        token = payment.token
        if not token:
            raise HTTPException(status_code=400, detail={"code": "missing_payment_token", "message": "Missing payment token"})

        verified, reason = verify_hyperswitch_payment(
            payment_id=token,
            amount=int(total_amount),
            currency=payment_currency or "",
        )
        if not verified:
            raise HTTPException(status_code=400, detail={"code": "payment_not_verified", "message": f"Payment not verified: {reason}"})

        now = datetime.now(timezone.utc)
        order_id = f"ord_{uuid4().hex}"
        order = OrderSummary(
            id=order_id,
            status="created",
            created_at=now,
        )

        session_data["status"] = "completed"
        session_data["order"] = jsonable_encoder(order)
        session_data["updated_at"] = now.isoformat() + "Z"

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

        _set_common_headers(request, response)
        return _apply_idempotency(
            request,
            response,
            body,
            session_data,
            status_code=201,
            store=store,
        )


@app.post("/orders/{order_id}/update")
async def update_order(
    order_id: str,
    payload: Dict[str, Any],
) -> JSONResponse:
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
