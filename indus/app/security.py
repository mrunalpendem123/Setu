from __future__ import annotations

import os
from uuid import uuid4


def _api_key() -> str | None:
    value = os.getenv("INDUS_API_KEY")
    return value if value else None


def build_headers() -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Request-Id": str(uuid4()),
    }
    api_key = _api_key()
    if api_key:
        headers["X-Indus-Key"] = api_key
    return headers
