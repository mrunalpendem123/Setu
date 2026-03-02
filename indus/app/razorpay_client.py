from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Dict, List, Optional

import httpx


class RazorpayAPIError(RuntimeError):
    def __init__(self, status_code: int, payload: Any):
        super().__init__(f"Razorpay API error {status_code}")
        self.status_code = status_code
        self.payload = payload


class RazorpayClient:
    """Razorpay API client using HTTP Basic Auth (key_id:key_secret)."""

    def __init__(self) -> None:
        self.key_id = os.getenv("RAZORPAY_KEY_ID", "")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
        self.base_url = "https://api.razorpay.com/v1"
        self.timeout = float(os.getenv("RAZORPAY_TIMEOUT_SECONDS", "20"))
        self.max_retries = int(os.getenv("RAZORPAY_MAX_RETRIES", "3"))
        self.backoff_ms = int(os.getenv("RAZORPAY_RETRY_BACKOFF_MS", "200"))

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        auth = (self.key_id, self.key_secret)

        for attempt in range(self.max_retries + 1):
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method,
                    url,
                    auth=auth,
                    json=payload,
                    params=params,
                )

            if response.status_code < 400:
                return response.json()

            # Retry on rate-limit
            if attempt < self.max_retries and response.status_code == 429:
                sleep_secs = (self.backoff_ms / 1000.0) * (2 ** attempt)
                time.sleep(sleep_secs)
                continue

            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"message": response.text}
            raise RazorpayAPIError(response.status_code, error_payload)

        raise RazorpayAPIError(500, {"message": "max_retries_exceeded"})

    # ── Orders ────────────────────────────────────────────────────────────────

    def create_order(
        self,
        amount: int,
        currency: str = "INR",
        receipt: str = "",
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /v1/orders → { id:"order_xxx", amount, currency, status }"""
        body: Dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt,
        }
        if notes:
            body["notes"] = notes
        return self._request("POST", "/orders", payload=body)

    # ── UPI Collect (server-to-server, agentic — no redirect) ─────────────────

    def create_upi_payment(
        self,
        order_id: str,
        vpa: str,
        contact: str,
        email: str,
        amount: int,
        currency: str = "INR",
    ) -> Dict[str, Any]:
        """POST /v1/payments/create/json — initiates UPI Collect (server-to-server)."""
        body: Dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "order_id": order_id,
            "method": "upi",
            "vpa": vpa,
            "contact": contact,
            "email": email,
        }
        return self._request("POST", "/payments/create/json", payload=body)

    # ── UPI QR Code ───────────────────────────────────────────────────────────

    def create_qr_code(
        self,
        name: str,
        description: str,
        amount: int,
        close_by_unix: int,
        usage: str = "single_use",
        fixed_amount: bool = True,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /v1/payments/qr-codes → { id:"qr_xxx", image_url, short_url }"""
        body: Dict[str, Any] = {
            "type": "upi_qr",
            "name": name,
            "usage": usage,
            "fixed_amount": fixed_amount,
            "payment_amount": amount,
            "description": description,
            "close_by": close_by_unix,
        }
        if notes:
            body["notes"] = notes
        return self._request("POST", "/payments/qr-codes", payload=body)

    # ── UPI Reserve Pay (SBMD / PIN-less agentic authorisation) ───────────────

    def create_upi_mandate(
        self,
        order_id: str,
        customer_id: str,
        vpa: str,
        max_amount: int,
        description: str = "Indus Agent Authorization",
        currency: str = "INR",
    ) -> Dict[str, Any]:
        """POST /v1/payments/create/upi_mandate → { id:"pay_xxx", status:"created" }"""
        body: Dict[str, Any] = {
            "order_id": order_id,
            "customer_id": customer_id,
            "vpa": vpa,
            "max_amount": max_amount,
            "currency": currency,
            "description": description,
            "type": "upi_mandate",
        }
        return self._request("POST", "/payments/create/upi_mandate", payload=body)

    # ── Payment lifecycle ─────────────────────────────────────────────────────

    def retrieve_payment(self, payment_id: str) -> Dict[str, Any]:
        """GET /v1/payments/{id}"""
        return self._request("GET", f"/payments/{payment_id}")

    def capture_payment(self, payment_id: str, amount: int, currency: str = "INR") -> Dict[str, Any]:
        """POST /v1/payments/{id}/capture"""
        return self._request(
            "POST",
            f"/payments/{payment_id}/capture",
            payload={"amount": amount, "currency": currency},
        )

    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[int] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /v1/payments/{id}/refund"""
        body: Dict[str, Any] = {}
        if amount is not None:
            body["amount"] = amount
        if notes:
            body["notes"] = notes
        return self._request("POST", f"/payments/{payment_id}/refund", payload=body)

    # ── Razorpay Route — merchant settlement ──────────────────────────────────

    def create_transfer(
        self,
        payment_id: str,
        account_id: str,
        amount: int,
        currency: str = "INR",
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /v1/payments/{id}/transfers — split to merchant linked account."""
        transfer: Dict[str, Any] = {
            "account": account_id,
            "amount": amount,
            "currency": currency,
        }
        if notes:
            transfer["notes"] = notes
        return self._request(
            "POST",
            f"/payments/{payment_id}/transfers",
            payload={"transfers": [transfer]},
        )

    # ── Linked account (Route onboarding) ─────────────────────────────────────

    def create_linked_account(
        self,
        legal_name: str,
        email: str,
        profile: Dict[str, Any],
        legal_info: Dict[str, Any],
        bank_account: Dict[str, Any],
    ) -> Dict[str, Any]:
        """POST /v1/accounts — onboard a merchant on Razorpay Route."""
        body: Dict[str, Any] = {
            "email": email,
            "profile": profile,
            "legal_info": legal_info,
            "bank_account": bank_account,
            "legal_business_name": legal_name,
            "business_type": "individual",
        }
        return self._request("POST", "/accounts", payload=body)

    # ── Customer ──────────────────────────────────────────────────────────────

    def create_customer(
        self,
        name: str,
        email: str,
        contact: str,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /v1/customers"""
        body: Dict[str, Any] = {"name": name, "email": email, "contact": contact}
        if notes:
            body["notes"] = notes
        return self._request("POST", "/customers", payload=body)

    # ── Webhook signature verification ───────────────────────────────────────

    @staticmethod
    def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
        """HMAC-SHA256 signature check (Razorpay standard)."""
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
