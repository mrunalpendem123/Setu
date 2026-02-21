from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_seconds: int


class RateLimiter:
    def __init__(self) -> None:
        self.window_seconds = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
        self.max_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
        self._state: Dict[str, Tuple[int, float]] = {}

    def _now(self) -> float:
        return time.monotonic()

    def check(self, key: str) -> RateLimitResult:
        now = self._now()
        count, reset_at = self._state.get(key, (0, now + self.window_seconds))
        if now >= reset_at:
            count = 0
            reset_at = now + self.window_seconds

        count += 1
        self._state[key] = (count, reset_at)

        allowed = count <= self.max_requests
        remaining = max(self.max_requests - count, 0)
        reset_seconds = max(int(reset_at - now), 0)
        return RateLimitResult(allowed=allowed, remaining=remaining, reset_seconds=reset_seconds)
