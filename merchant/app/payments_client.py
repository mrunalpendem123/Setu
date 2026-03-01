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

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        response = self.client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    def retrieve_payment(self, payment_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", f"/payments/{payment_id}", params=params)

    def create_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/payments", json=payload)

    def update_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}", json=payload)

    def confirm_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/confirm", json=payload)

    def cancel_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/cancel", json=payload)

    def capture_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/capture", json=payload)

    def create_refund(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/refunds", json=payload)

    def complete_authorize(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/complete_authorize", json=payload)

    def create_external_sdk_tokens(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/create_external_sdk_tokens", json=payload)


def payments_service_enabled() -> bool:
    return _service_url() is not None
