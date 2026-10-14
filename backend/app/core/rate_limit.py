"""Minimal in-process sliding-window rate limiter.

Expensive endpoints (uploads, provider refreshes, matching, assistant calls,
login attempts) are protected per user (or per client IP when anonymous).

This limiter keeps state in memory, which is correct for a single API process.
A multi-process or multi-host deployment should replace it with a shared
store such as Redis — see docs/PRIVACY_AND_SECURITY.md.
"""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque

from fastapi import status

from app.core.errors import AppError


def parse_rate(rate: str) -> tuple[int, int]:
    count, _, seconds = rate.partition("/")
    return int(count), int(seconds)


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, bucket: str, key: str, rate: str) -> None:
        limit, window = parse_rate(rate)
        now = time.monotonic()
        full_key = f"{bucket}:{key}"
        with self._lock:
            hits = self._hits[full_key]
            while hits and now - hits[0] >= window:
                hits.popleft()
            if len(hits) >= limit:
                retry_after = max(1, math.ceil(window - (now - hits[0])))
                raise AppError(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "rate_limited",
                    "Too many requests. Please wait before trying again.",
                    details={"retry_after_seconds": retry_after},
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()
