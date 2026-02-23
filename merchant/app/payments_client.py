from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx


def _service_url() -> str | None:
    value = os.getenv("PAYMENTS_SERVICE_URL")
    return value.rstrip("/") if value else None


def _timeout() -> float:
    return float(os.getenv("PAYMENTS_SERVICE_TIMEOUT_SECONDS", "20"))


class PaymentsServiceClient:
    def __init__(self) -> None:
        base = _service_url()
        if not base:
            raise RuntimeError("PAYMENTS_SERVICE_URL is not set")
        self.base_url = base
        self.timeout = _timeout()
        self.client = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def retrieve_payment(self, payment_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.client.get(f"/payments/{payment_id}", params=params)
        response.raise_for_status()
        return response.json()


def payments_service_enabled() -> bool:
    return _service_url() is not None
