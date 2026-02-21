from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import httpx


class SarvamAPIError(RuntimeError):
    def __init__(self, status_code: int, payload: Any):
        super().__init__(f"Sarvam API error {status_code}")
        self.status_code = status_code
        self.payload = payload


def _base_url() -> str:
    value = os.getenv("SARVAM_BASE_URL")
    if not value:
        raise RuntimeError("SARVAM_BASE_URL is not set")
    return value


def _api_key() -> str:
    value = os.getenv("SARVAM_API_KEY")
    if not value:
        raise RuntimeError("SARVAM_API_KEY is not set")
    return value


def _api_key_header() -> str:
    return os.getenv("SARVAM_API_KEY_HEADER", "api-subscription-key")


def _timeout_seconds() -> float:
    return float(os.getenv("SARVAM_TIMEOUT_SECONDS", "20"))


def _max_retries() -> int:
    return int(os.getenv("SARVAM_MAX_RETRIES", "2"))


def _retry_backoff_ms() -> int:
    return int(os.getenv("SARVAM_RETRY_BACKOFF_MS", "200"))


def _proxy_path() -> str:
    value = os.getenv("SARVAM_PROXY_PATH")
    if not value:
        raise RuntimeError("SARVAM_PROXY_PATH is not set")
    return value


class SarvamClient:
    def __init__(self) -> None:
        self.base_url = _base_url().rstrip("/")
        self.api_key = _api_key()
        self.api_key_header = _api_key_header()
        self.timeout = _timeout_seconds()

    def request(self, payload: Dict[str, Any], path: Optional[str] = None) -> Dict[str, Any]:
        max_retries = _max_retries()
        backoff_ms = _retry_backoff_ms()
        headers = {
            self.api_key_header: self.api_key,
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}{path or _proxy_path()}"

        for attempt in range(max_retries + 1):
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code < 400:
                return response.json()

            if attempt < max_retries and response.status_code in {429, 500, 502, 503, 504}:
                sleep_seconds = (backoff_ms / 1000.0) * (2**attempt)
                time.sleep(sleep_seconds)
                continue

            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"message": response.text}
            raise SarvamAPIError(response.status_code, error_payload)

        raise SarvamAPIError(500, {"message": "max_retries_exceeded"})
