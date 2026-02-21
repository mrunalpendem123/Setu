from __future__ import annotations

from datetime import datetime

from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.encoders import jsonable_encoder

from .models import (
    IndusCreateCheckoutRequest,
    IndusUpdateCheckoutRequest,
    IndusCheckoutResponse,
    PaymentIntentRequest,
    PaymentIntentResponse,
    CompleteCheckoutRequest,
    CompleteCheckoutResponse,
)
from .merchant_client import MerchantClient
from .hyperswitch import HyperswitchClient, HyperswitchAPIError
from .db import init_db, get_db, SessionRecord, PaymentRecord, OrderEvent


app = FastAPI(title="Indus Orchestrator", version="1.0.0")


def _raise_hyperswitch_error(exc: HyperswitchAPIError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.payload)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.post("/indus/checkout", response_model=IndusCheckoutResponse)
def create_checkout(payload: IndusCreateCheckoutRequest) -> IndusCheckoutResponse:
    merchant = MerchantClient(payload.merchant_base_url)
    merchant_payload = payload.model_dump(exclude={"merchant_base_url"}, exclude_none=True)
    session = merchant.create_checkout_session(merchant_payload)

    session_id = session.get("id")
    if not session_id:
        raise HTTPException(status_code=502, detail="merchant_invalid_response")

    with get_db() as db:
        db.merge(
            SessionRecord(
                session_id=session_id,
                merchant_base_url=payload.merchant_base_url,
                session_data=session,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
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
    session = merchant.update_checkout_session(
        session_id,
        payload.model_dump(exclude_none=True),
    )

    with get_db() as db:
        record = db.get(SessionRecord, session_id)
        if record:
            record.session_data = session
            record.updated_at = datetime.utcnow()
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
            record.updated_at = datetime.utcnow()
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
            record.updated_at = datetime.utcnow()
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

    client = HyperswitchClient()
    request_data = payload.model_dump(exclude_none=True)
    metadata = dict(request_data.get("metadata") or {})
    metadata.setdefault("checkout_session_id", session_id)
    request_data["metadata"] = metadata
    try:
        record_data = client.create_payment_intent(request_data)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)

    payment_id = record_data.get("payment_id") or record_data.get("id")
    if not payment_id:
        raise HTTPException(status_code=502, detail="hyperswitch_missing_payment_id")

    with get_db() as db:
        db.merge(
            PaymentRecord(
                payment_id=payment_id,
                status=record_data.get("status", "unknown"),
                data=record_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        db.commit()

    return PaymentIntentResponse(
        payment_id=payment_id,
        client_secret=record_data.get("client_secret", ""),
        status=record_data.get("status", "unknown"),
    )


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


@app.post("/indus/payments")
def hyperswitch_create_payment(payload: Dict[str, Any]) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.create_payment(payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}")
def hyperswitch_update_payment(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.update_payment(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/confirm")
def hyperswitch_confirm_payment(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.confirm_payment(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.get("/indus/payments/{payment_id}")
def hyperswitch_retrieve_payment(
    payment_id: str,
    request: Request,
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.retrieve_payment(payment_id, params=dict(request.query_params))
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/cancel")
def hyperswitch_cancel_payment(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.cancel_payment(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/cancel_post_capture")
def hyperswitch_cancel_post_capture(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.cancel_payment_post_capture(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/capture")
def hyperswitch_capture_payment(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.capture_payment(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/incremental_authorization")
def hyperswitch_incremental_authorization(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.incremental_authorization(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/extend_authorization")
def hyperswitch_extend_authorization(payment_id: str) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.extend_authorization(payment_id)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/session_tokens")
def hyperswitch_session_tokens(payload: Dict[str, Any]) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.create_session_token(payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.get("/indus/payment_links/{payment_link_id}")
def hyperswitch_payment_link_retrieve(payment_link_id: str) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.retrieve_payment_link(payment_link_id)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.get("/indus/payments")
def hyperswitch_list_payments(request: Request) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.list_payments(params=dict(request.query_params))
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/3ds/authentication")
def hyperswitch_external_3ds(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.external_3ds_authentication(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/complete_authorize")
def hyperswitch_complete_authorize(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.complete_authorize(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/update_metadata")
def hyperswitch_update_metadata(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.update_metadata(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payments/{payment_id}/eligibility")
def hyperswitch_submit_eligibility(
    payment_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.submit_eligibility(payment_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/payment_method_sessions")
def hyperswitch_payment_method_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.create_payment_method_session(payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/indus/api_keys/{merchant_id}")
def hyperswitch_create_api_key(
    merchant_id: str,
    payload: Dict[str, Any] = Body(default={}),
) -> Dict[str, Any]:
    client = HyperswitchClient()
    try:
        return client.create_api_key(merchant_id, payload)
    except HyperswitchAPIError as exc:
        _raise_hyperswitch_error(exc)


@app.post("/webhooks/orders")
async def order_webhook(payload: dict) -> dict:
    with get_db() as db:
        db.add(OrderEvent(payload=jsonable_encoder(payload)))
        db.commit()
    return {"status": "received"}
