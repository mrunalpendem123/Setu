from __future__ import annotations

import os
import time
from typing import Dict, Any, Optional

import httpx


def _api_base() -> str:
    return os.getenv("HYPERSWITCH_BASE_URL", "https://sandbox.hyperswitch.io")


def _api_key() -> str:
    value = os.getenv("HYPERSWITCH_API_KEY")
    if not value:
        raise RuntimeError("HYPERSWITCH_API_KEY is not set")
    return value


def _publishable_key() -> str:
    value = os.getenv("HYPERSWITCH_PUBLISHABLE_KEY")
    if not value:
        raise RuntimeError("HYPERSWITCH_PUBLISHABLE_KEY is not set")
    return value


def _admin_api_key() -> str:
    value = os.getenv("HYPERSWITCH_ADMIN_API_KEY")
    if not value:
        raise RuntimeError("HYPERSWITCH_ADMIN_API_KEY is not set")
    return value


def _vault_api_key() -> str:
    value = os.getenv("HYPERSWITCH_VAULT_API_KEY")
    if not value:
        raise RuntimeError("HYPERSWITCH_VAULT_API_KEY is not set")
    return value


def _api_key_header() -> str:
    return os.getenv("HYPERSWITCH_API_KEY_HEADER", "api-key")


def _merchant_id() -> str | None:
    return os.getenv("HYPERSWITCH_MERCHANT_ID")


def _timeout_seconds() -> float:
    return float(os.getenv("HYPERSWITCH_TIMEOUT_SECONDS", "20"))


def _max_retries() -> int:
    return int(os.getenv("HYPERSWITCH_MAX_RETRIES", "3"))


def _retry_backoff_ms() -> int:
    return int(os.getenv("HYPERSWITCH_RETRY_BACKOFF_MS", "200"))


def _payment_method_session_path() -> str:
    return os.getenv("HYPERSWITCH_PAYMENT_METHOD_SESSION_PATH", "/v2/payment-method-session")


class HyperswitchAPIError(RuntimeError):
    def __init__(self, status_code: int, payload: Any):
        super().__init__(f"Hyperswitch API error {status_code}")
        self.status_code = status_code
        self.payload = payload


class HyperswitchClient:
    def __init__(self) -> None:
        self.base_url = _api_base().rstrip("/")
        self.api_key_header = _api_key_header()
        self.merchant_id = _merchant_id()
        self.timeout = _timeout_seconds()

    def _headers(
        self,
        use_publishable_key: bool,
        use_admin_key: bool,
        use_vault_key: bool,
    ) -> Dict[str, str]:
        if use_admin_key:
            api_key = _admin_api_key()
        elif use_vault_key:
            api_key = _vault_api_key()
        else:
            api_key = _publishable_key() if use_publishable_key else _api_key()
        headers = {
            self.api_key_header: api_key,
            "Content-Type": "application/json",
        }
        if self.merchant_id:
            headers["x-merchant-id"] = self.merchant_id
        return headers

    def _should_retry(self, response: httpx.Response) -> bool:
        if response.status_code == 429:
            return True
        try:
            data = response.json()
        except ValueError:
            return False
        message = str(data.get("message", "")).lower()
        return "access to this object is restricted" in message

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_publishable_key: bool = False,
        use_admin_key: bool = False,
        use_vault_key: bool = False,
    ) -> Dict[str, Any]:
        max_retries = _max_retries()
        backoff_ms = _retry_backoff_ms()
        url = f"{self.base_url}{path}"
        headers = self._headers(use_publishable_key, use_admin_key, use_vault_key)

        for attempt in range(max_retries + 1):
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method,
                    url,
                    headers=headers,
                    json=payload,
                    params=params,
                )

            if response.status_code < 400:
                return response.json()

            if attempt < max_retries and self._should_retry(response):
                sleep_seconds = (backoff_ms / 1000.0) * (2**attempt)
                time.sleep(sleep_seconds)
                continue

            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"message": response.text}
            raise HyperswitchAPIError(response.status_code, error_payload)

        raise HyperswitchAPIError(500, {"message": "max_retries_exceeded"})

    def create_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/payments", payload=payload)

    def update_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}", payload=payload)

    def confirm_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/confirm", payload=payload)

    def retrieve_payment(self, payment_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", f"/payments/{payment_id}", params=params)

    def cancel_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/cancel", payload=payload)

    def cancel_payment_post_capture(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/cancel_post_capture", payload=payload)

    def capture_payment(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/capture", payload=payload)

    def incremental_authorization(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/incremental_authorization", payload=payload)

    def extend_authorization(self, payment_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/extend_authorization")

    def create_session_token(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/payments/session_tokens", payload=payload, use_publishable_key=True)

    def retrieve_payment_link(self, payment_link_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/payment_link/{payment_link_id}", use_publishable_key=True)

    def list_payments(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._request("GET", "/payments/list", params=params)

    def external_3ds_authentication(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/3ds/authentication", payload=payload)

    def complete_authorize(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/{payment_id}/complete_authorize", payload=payload)

    def update_metadata(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/update_metadata", payload=payload)

    def submit_eligibility(self, payment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/payments/{payment_id}/eligibility", payload=payload)

    def create_payment_method_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request(
            "POST",
            _payment_method_session_path(),
            payload=payload,
            use_vault_key=True,
        )

    def create_api_key(self, merchant_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", f"/api_keys/{merchant_id}", payload=payload, use_admin_key=True)

    def create_payment_intent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.create_payment(payload)
