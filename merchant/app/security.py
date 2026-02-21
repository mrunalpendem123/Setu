from __future__ import annotations

import os
from fastapi import HTTPException, Request


def _api_keys() -> set[str]:
    raw = os.getenv("INDUS_API_KEYS", "")
    return {value.strip() for value in raw.split(",") if value.strip()}


def validate_request(request: Request, body: bytes) -> None:
    # Optional API key auth for service-to-service calls
    keys = _api_keys()
    if not keys:
        return

    token = request.headers.get("X-Indus-Key")
    if not token or token not in keys:
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Invalid API key"})
