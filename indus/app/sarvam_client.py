from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import httpx

# Sarvam-M is a 24B multilingual model supporting 11 Indic languages.
# API: POST https://api.sarvam.ai/v1/chat/completions
# Auth: api-subscription-key header
# Switch to sarvam-105b by setting SARVAM_MODEL=sarvam-105b once available.
SARVAM_CHAT_PATH = "/v1/chat/completions"
SARVAM_DEFAULT_MODEL = "sarvam-m"


class SarvamAPIError(RuntimeError):
    def __init__(self, status_code: int, payload: Any):
        super().__init__(f"Sarvam API error {status_code}")
        self.status_code = status_code
        self.payload = payload


def _base_url() -> str:
    return os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai").rstrip("/")


def _api_key() -> str:
    value = os.getenv("SARVAM_API_KEY")
    if not value:
        raise RuntimeError("SARVAM_API_KEY is not set")
    return value


def _model() -> str:
    return os.getenv("SARVAM_MODEL", SARVAM_DEFAULT_MODEL)


def _api_key_header() -> str:
    return os.getenv("SARVAM_API_KEY_HEADER", "api-subscription-key")


def _timeout_seconds() -> float:
    return float(os.getenv("SARVAM_TIMEOUT_SECONDS", "20"))


def _max_retries() -> int:
    return int(os.getenv("SARVAM_MAX_RETRIES", "2"))


def _retry_backoff_ms() -> int:
    return int(os.getenv("SARVAM_RETRY_BACKOFF_MS", "200"))


class SarvamClient:
    def __init__(self) -> None:
        self.base_url = _base_url()
        self.api_key = _api_key()
        self.timeout = _timeout_seconds()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        max_retries = _max_retries()
        backoff_ms = _retry_backoff_ms()
        headers = {
            _api_key_header(): self.api_key,
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}{path}"

        for attempt in range(max_retries + 1):
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code < 400:
                return response.json()

            if attempt < max_retries and response.status_code in {429, 500, 502, 503, 504}:
                time.sleep((backoff_ms / 1000.0) * (2 ** attempt))
                continue

            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"message": response.text}
            raise SarvamAPIError(response.status_code, error_payload)

        raise SarvamAPIError(500, {"message": "max_retries_exceeded"})

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        wiki_grounding: bool = False,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call Sarvam-M (or configured model) via chat completions."""
        payload: Dict[str, Any] = {
            "model": model or _model(),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if wiki_grounding:
            payload["wiki_grounding"] = True
        return self._post(SARVAM_CHAT_PATH, payload)

    def request(self, payload: Dict[str, Any], path: Optional[str] = None) -> Dict[str, Any]:
        """Generic proxy — passes payload as-is to the given path (or SARVAM_PROXY_PATH)."""
        proxy_path = path or os.getenv("SARVAM_PROXY_PATH", SARVAM_CHAT_PATH)
        return self._post(proxy_path, payload)
