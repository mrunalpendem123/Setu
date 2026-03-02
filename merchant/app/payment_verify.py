from __future__ import annotations

import os
import time
from typing import Tuple, Set, Any

import httpx

from .payments_client import PaymentsServiceClient, payments_service_enabled


class PaymentVerificationError(RuntimeError):
    pass


def _key_id() -> str:
    value = os.getenv("RAZORPAY_KEY_ID")
    if not value:
        raise PaymentVerificationError("RAZORPAY_KEY_ID is not set")
    return value


def _key_secret() -> str:
    value = os.getenv("RAZORPAY_KEY_SECRET")
    if not value:
        raise PaymentVerificationError("RAZORPAY_KEY_SECRET is not set")
    return value


def _timeout_seconds() -> float:
    return float(os.getenv("RAZORPAY_TIMEOUT_SECONDS", "20"))


def _max_retries() -> int:
    return int(os.getenv("RAZORPAY_MAX_RETRIES", "3"))


def _retry_backoff_ms() -> int:
    return int(os.getenv("RAZORPAY_RETRY_BACKOFF_MS", "200"))


def _accepted_statuses() -> Set[str]:
    raw = os.getenv(
        "RAZORPAY_ACCEPTED_STATUSES",
        "captured,authorized,requires_customer_action",
    )
    return {value.strip() for value in raw.split(",") if value.strip()}


def _should_retry(response: httpx.Response) -> bool:
    return response.status_code == 429


def verify_razorpay_payment(
    payment_id: str,
    amount: int,
    currency: str,
) -> Tuple[bool, str]:
    """Verify a Razorpay payment by retrieving its status from the API.

    Returns (True, "verified") on success, (True, "pending_customer_action")
    for UPI flows awaiting user approval, and (False, reason) on failure.
    """
    if not payment_id or amount <= 0 or not currency:
        return False, "invalid_payment_data"

    # UPI QR codes and order IDs are not verifiable via /payments/{id}
    if payment_id.startswith("qr_") or payment_id.startswith("order_"):
        return True, "pending_customer_action"

    # Delegated PSP tokens
    if payment_id.startswith("vt_"):
        if not payments_service_enabled():
            return False, "delegated_psp_not_configured"
        try:
            client = PaymentsServiceClient()
            data: Any = client.retrieve_payment(payment_id)
        except Exception:
            return False, "payments_service_error"
        return _evaluate_payment(data, amount, currency)

    # Direct Razorpay payment lookup
    base_url = "https://api.razorpay.com/v1"
    max_retries = _max_retries()
    backoff_ms = _retry_backoff_ms()
    timeout = _timeout_seconds()
    data: Any = None

    try:
        key_id = _key_id()
        key_secret = _key_secret()
    except PaymentVerificationError as exc:
        return False, str(exc)

    for attempt in range(max_retries + 1):
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                f"{base_url}/payments/{payment_id}",
                auth=(key_id, key_secret),
            )

        if response.status_code < 400:
            data = response.json()
            break

        if attempt < max_retries and _should_retry(response):
            sleep_seconds = (backoff_ms / 1000.0) * (2 ** attempt)
            time.sleep(sleep_seconds)
            continue

        return False, f"razorpay_error:{response.status_code}"

    if data is None:
        return False, "razorpay_error"

    return _evaluate_payment(data, amount, currency)


def _evaluate_payment(data: Any, amount: int, currency: str) -> Tuple[bool, str]:
    returned_amount = data.get("amount")
    returned_currency = data.get("currency")
    status = data.get("status", "")

    if returned_amount is not None and int(returned_amount) != int(amount):
        return False, "amount_mismatch"
    if returned_currency and returned_currency.upper() != currency.upper():
        return False, "currency_mismatch"

    if status in ("captured", "authorized"):
        return True, "verified"
    elif status == "created":
        # UPI Collect initiated but user hasn't approved yet
        return True, "pending_customer_action"
    elif status in ("requires_customer_action",):
        return True, "pending_customer_action"
    elif status == "failed":
        return False, "payment_failed"
    elif status not in _accepted_statuses():
        return False, f"unexpected_status:{status}"

    return True, "verified"
