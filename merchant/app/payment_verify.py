from __future__ import annotations

import os
import time
from typing import Tuple, Set, Any

import httpx

from .payments_client import PaymentsServiceClient, payments_service_enabled

class PaymentVerificationError(RuntimeError):
    pass


def _api_base() -> str:
    return os.getenv("HYPERSWITCH_BASE_URL", "https://sandbox.hyperswitch.io")


def _api_key() -> str:
    value = os.getenv("HYPERSWITCH_API_KEY")
    if not value:
        raise PaymentVerificationError("HYPERSWITCH_API_KEY is not set")
    return value


def _api_key_header() -> str:
    return os.getenv("HYPERSWITCH_API_KEY_HEADER", "api-key")


def _merchant_id() -> str | None:
    return os.getenv("HYPERSWITCH_MERCHANT_ID")


def _profile_id() -> str | None:
    return os.getenv("HYPERSWITCH_PROFILE_ID")


def _timeout_seconds() -> float:
    return float(os.getenv("HYPERSWITCH_TIMEOUT_SECONDS", "20"))


def _max_retries() -> int:
    return int(os.getenv("HYPERSWITCH_MAX_RETRIES", "3"))


def _retry_backoff_ms() -> int:
    return int(os.getenv("HYPERSWITCH_RETRY_BACKOFF_MS", "200"))


def _accepted_statuses() -> Set[str]:
    raw = os.getenv(
        "HYPERSWITCH_ACCEPTED_STATUSES",
        "succeeded,processing,requires_capture,requires_customer_action",
    )
    return {value.strip() for value in raw.split(",") if value.strip()}


def _should_retry(response: httpx.Response) -> bool:
    if response.status_code == 429:
        return True
    try:
        data: Any = response.json()
    except ValueError:
        return False
    message = str(data.get("message", "")).lower()
    return "access to this object is restricted" in message


def verify_hyperswitch_payment(
    payment_id: str,
    amount: int,
    currency: str,
) -> Tuple[bool, str]:
    if not payment_id or amount <= 0 or not currency:
        return False, "invalid_payment_data"

    if payments_service_enabled():
        try:
            client = PaymentsServiceClient()
            data: Any = client.retrieve_payment(payment_id)
        except Exception:
            return False, "payments_service_error"
    else:
        base_url = _api_base().rstrip("/")
        headers = {
            _api_key_header(): _api_key(),
            "Content-Type": "application/json",
        }

        merchant_id = _merchant_id()
        if merchant_id:
            headers["x-merchant-id"] = merchant_id
        profile_id = _profile_id()
        if profile_id:
            headers["X-Profile-Id"] = profile_id

        max_retries = _max_retries()
        backoff_ms = _retry_backoff_ms()
        timeout = _timeout_seconds()
        data: Any = None

        for attempt in range(max_retries + 1):
            with httpx.Client(base_url=base_url, headers=headers, timeout=timeout) as client:
                response = client.get(f"/payments/{payment_id}")

            if response.status_code < 400:
                data = response.json()
                break

            if attempt < max_retries and _should_retry(response):
                sleep_seconds = (backoff_ms / 1000.0) * (2**attempt)
                time.sleep(sleep_seconds)
                continue

            return False, f"hyperswitch_error:{response.status_code}"

        if data is None:
            return False, "hyperswitch_error"

    status = data.get("status")
    returned_amount = data.get("amount")
    returned_currency = data.get("currency")

    if returned_amount is not None and int(returned_amount) != int(amount):
        return False, "amount_mismatch"
    if returned_currency and returned_currency.lower() != currency.lower():
        return False, "currency_mismatch"

    if status == "requires_customer_action":
        return True, "pending_customer_action"

    # Card 3DS — agent must collect authentication result before re-submitting
    if status == "requires_authentication":
        return False, "requires_3ds"

    if status not in _accepted_statuses():
        return False, f"unexpected_status:{status}"

    return True, "verified"
