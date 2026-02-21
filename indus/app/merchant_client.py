from __future__ import annotations

from typing import Dict, Any

import httpx

from .security import build_headers


class MerchantClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=10.0)

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = build_headers()
        response = self.client.post(path, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    def _get(self, path: str) -> Dict[str, Any]:
        headers = build_headers()
        response = self.client.get(path, headers=headers)
        response.raise_for_status()
        return response.json()

    def create_checkout_session(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/checkout_sessions", payload)

    def update_checkout_session(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/checkout_sessions/{session_id}", payload)

    def cancel_checkout_session(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/checkout_sessions/{session_id}/cancel", payload)

    def complete_checkout_session(self, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post(f"/checkout_sessions/{session_id}/complete", payload)

    def get_checkout_session(self, session_id: str) -> Dict[str, Any]:
        return self._get(f"/checkout_sessions/{session_id}")
