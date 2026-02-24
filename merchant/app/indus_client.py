from __future__ import annotations

import os
from typing import Any, Dict

import httpx


class IndusClientError(RuntimeError):
    def __init__(self, status_code: int, payload: Any):
        super().__init__(f"Indus API error: {status_code}")
        self.status_code = status_code
        self.payload = payload


def _base_url() -> str:
    value = os.getenv("INDUS_BASE_URL")
    if not value:
        raise IndusClientError(503, {"code": "indus_not_configured", "message": "INDUS_BASE_URL not set"})
    return value.rstrip("/")


def _api_key() -> str | None:
    value = os.getenv("INDUS_API_KEY")
    return value if value else None


class IndusClient:
    def __init__(self) -> None:
        self.base_url = _base_url()
        self.client = httpx.Client(base_url=self.base_url, timeout=10.0)

    def redeem_token(self, token: str, purpose: str | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if purpose:
            payload["purpose"] = purpose
        headers = {"Content-Type": "application/json"}
        api_key = _api_key()
        if api_key:
            headers["X-Indus-Key"] = api_key
        response = self.client.post(f"/indus/tokens/{token}/redeem", json=payload, headers=headers)
        if response.status_code >= 400:
            raise IndusClientError(response.status_code, response.json())
        return response.json()
