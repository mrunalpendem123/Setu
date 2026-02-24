from __future__ import annotations

import os
from uuid import uuid4

from fastapi import HTTPException, Request


def _api_key() -> str | None:
    value = os.getenv("INDUS_API_KEY")
    return value if value else None


def _merchant_api_keys() -> set[str]:
    raw = os.getenv("MERCHANT_API_KEYS", "")
    return {value.strip() for value in raw.split(",") if value.strip()}


def build_headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Request-Id": str(uuid4()),
    }
    api_key = _api_key()
    if api_key:
        headers["X-Indus-Key"] = api_key
    return headers


def validate_merchant_request(request: Request) -> None:
    keys = _merchant_api_keys()
    if not keys:
        return

    token = request.headers.get("X-Indus-Key")
    if not token or token not in keys:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid API key"})
