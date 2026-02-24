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

    def create_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/payments", payload)

    def update_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}", payload)

    def confirm_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/confirm", payload)

    def retrieve_payment(self, payment_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._get(f"/payments/{payment_id}", params)

    def cancel_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/cancel", payload)

    def cancel_post_capture(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/cancel_post_capture", payload)

    def capture_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/capture", payload)

    def incremental_authorization(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/incremental_authorization", payload)

    def extend_authorization(self, payment_id: str) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/extend_authorization", {})

    def session_tokens(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/payments/session_tokens", payload)

    def payment_link(self, payment_link_id: str) -> Dict[str, Any]:
        return self._get(f"/payment_links/{payment_link_id}")

    def list_payments(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._get("/payments", params)

    def confirm_intent(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/confirm_intent", payload)

    def payment_methods(self, payment_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._get(f"/payments/{payment_id}/payment_methods", params)

    def create_external_sdk_tokens(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/create_external_sdk_tokens", payload)

    def external_3ds(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/3ds/authentication", payload)

    def complete_authorize(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/complete_authorize", payload)

    def update_metadata(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/update_metadata", payload)

    def submit_eligibility(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/payments/{payment_id}/eligibility", payload)

    def payment_method_sessions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/payment_method_sessions", payload)

    def create_api_key(self, merchant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/api_keys/{merchant_id}", payload)

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.client.get(path, params=params)
        if response.status_code >= 400:
            raise PaymentsServiceError(response.status_code, response.json())
        return response.json()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.post(path, json=payload)
        if response.status_code >= 400:
            raise PaymentsServiceError(response.status_code, response.json())
        return response.json()


def payments_service_enabled() -> bool:
    return _service_url() is not None


class PaymentsServiceError(RuntimeError):
    def __init__(self, status_code: int, payload: Dict[str, Any]):
        super().__init__(f\"Payments service error {status_code}\")
        self.status_code = status_code
        self.payload = payload
