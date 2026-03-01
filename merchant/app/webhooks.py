from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

import httpx


def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _timeout_seconds() -> float:
    return float(os.getenv("ORDER_WEBHOOK_TIMEOUT_SECONDS", "5"))


def _max_retries() -> int:
    return int(os.getenv("ORDER_WEBHOOK_MAX_RETRIES", "3"))


def _retry_backoff_ms() -> int:
    return int(os.getenv("ORDER_WEBHOOK_RETRY_BACKOFF_MS", "200"))


def _format_event_name(event_type: str) -> str:
    style = os.getenv("ORDER_EVENT_STYLE", "dot")
    if style == "underscore":
        return event_type.replace(".", "_")
    return event_type


def warn_if_webhook_insecure() -> None:
    """Call at app startup — logs a warning if webhook is configured without a signing secret."""
    import logging as _log
    url = os.getenv("ORDER_WEBHOOK_URL")
    secret = os.getenv("ORDER_WEBHOOK_SECRET", "")
    if url and not secret:
        _log.getLogger("merchant.webhooks").warning(
            "ORDER_WEBHOOK_URL is set but ORDER_WEBHOOK_SECRET is not. "
            "Webhook events will be sent unsigned — any receiver cannot verify their authenticity. "
            "Set ORDER_WEBHOOK_SECRET to enable HMAC-SHA256 request signing."
        )


def send_order_event(event_type: str, payload: Dict[str, Any]) -> None:
    url = os.getenv("ORDER_WEBHOOK_URL")
    if not url:
        return

    secret = os.getenv("ORDER_WEBHOOK_SECRET", "")
    event_name = _format_event_name(event_type)
    event = {
        "id": f"evt_{uuid4().hex}",
        "type": event_name,
        "version": "2026-02-24",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "data": payload,
    }
    body = json.dumps(event).encode()
    headers = {"Content-Type": "application/json"}

    if secret:
        headers["Merchant-Signature"] = _signature(secret, body)

    timeout = _timeout_seconds()
    max_retries = _max_retries()
    backoff_ms = _retry_backoff_ms()

    for attempt in range(max_retries + 1):
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, content=body, headers=headers)

        if response.status_code < 400:
            return

        if attempt >= max_retries:
            return

        sleep_seconds = (backoff_ms / 1000.0) * (2**attempt)
        time.sleep(sleep_seconds)
