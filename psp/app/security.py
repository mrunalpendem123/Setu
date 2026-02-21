from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import HTTPException, Request


def _get_api_keys() -> set[str]:
    keys = os.getenv("ACP_API_KEYS", "")
    return {key.strip() for key in keys.split(",") if key.strip()}


def _get_api_versions() -> set[str]:
    versions = os.getenv("ACP_API_VERSIONS")
    if versions:
        return {value.strip() for value in versions.split(",") if value.strip()}
    return {os.getenv("ACP_API_VERSION", "2025-09-29")}


def _get_signature_secret() -> str | None:
    value = os.getenv("ACP_SIGNATURE_SECRET")
    return value if value else None


def _get_timestamp_tolerance_seconds() -> int:
    try:
        return int(os.getenv("ACP_TIMESTAMP_TOLERANCE_SECONDS", "300"))
    except ValueError:
        return 300


def _parse_authorization(header: str | None) -> str | None:
    if not header:
        return None
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def _validate_timestamp(timestamp_header: str | None) -> None:
    if not timestamp_header:
        return
    try:
        ts = datetime.fromisoformat(timestamp_header.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_timestamp") from exc

    now = datetime.now(timezone.utc)
    delta = abs((now - ts).total_seconds())
    tolerance = _get_timestamp_tolerance_seconds()
    if delta > tolerance:
        raise HTTPException(status_code=400, detail="timestamp_out_of_range")


def _compute_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _validate_signature(body: bytes, signature_header: str | None) -> None:
    secret = _get_signature_secret()
    if not secret:
        return
    if not signature_header:
        raise HTTPException(status_code=401, detail="missing_signature")

    expected = _compute_signature(secret, body)
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="invalid_signature")


def validate_request(request: Request, body: bytes) -> None:
    api_keys = _get_api_keys()
    api_versions = _get_api_versions()

    token = _parse_authorization(request.headers.get("Authorization"))
    if not token or (api_keys and token not in api_keys):
        raise HTTPException(status_code=401, detail="invalid_authorization")

    if request.headers.get("API-Version") not in api_versions:
        raise HTTPException(status_code=400, detail="invalid_api_version")

    _validate_timestamp(request.headers.get("Timestamp"))
    _validate_signature(body, request.headers.get("Signature"))
