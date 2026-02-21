from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Any, Dict

import httpx


def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _format_event_name(event_type: str) -> str:
    style = os.getenv("ORDER_EVENT_STYLE", "dot")
    if style == "underscore":
        return event_type.replace(".", "_")
    return event_type


def send_order_event(event_type: str, payload: Dict[str, Any]) -> None:
    url = os.getenv("ORDER_WEBHOOK_URL")
    if not url:
        return

    secret = os.getenv("ORDER_WEBHOOK_SECRET", "")
    event_name = _format_event_name(event_type)
    body = json.dumps({"type": event_name, "data": payload}).encode()
    headers = {"Content-Type": "application/json"}

    if secret:
        headers["Merchant-Signature"] = _signature(secret, body)

    with httpx.Client(timeout=5.0) as client:
        client.post(url, content=body, headers=headers)
