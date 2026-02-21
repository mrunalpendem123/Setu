from __future__ import annotations

import os
from typing import Tuple

import httpx


class DelegatedVerificationError(RuntimeError):
    pass


def _base_url() -> str | None:
    return os.getenv("DELEGATED_PSP_BASE_URL")


def _api_key() -> str | None:
    return os.getenv("DELEGATED_PSP_API_KEY")


def _api_version() -> str:
    return os.getenv("DELEGATED_PSP_API_VERSION", "2025-09-29")


def verify_delegated_token(token: str, amount: int, currency: str) -> Tuple[bool, str]:
    if not token or amount <= 0 or not currency:
        return False, "invalid_payment_data"

    base_url = _base_url()
    if not base_url:
        return False, "delegated_psp_not_configured"

    headers = {
        "Content-Type": "application/json",
        "API-Version": _api_version(),
    }
    api_key = _api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"amount": amount, "currency": currency}

    with httpx.Client(base_url=base_url.rstrip("/"), timeout=20.0) as client:
        response = client.post(f"/agentic_commerce/delegate_payment/{token}/redeem", json=payload, headers=headers)
        if response.status_code >= 400:
            return False, f"delegated_psp_error:{response.status_code}"
        data = response.json()

    if data.get("status") != "redeemed":
        return False, "token_not_redeemed"

    return True, "verified"
