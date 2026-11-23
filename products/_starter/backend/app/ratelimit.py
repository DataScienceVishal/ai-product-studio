"""Small in-process sliding-window rate limiter.

Per instance only: with several replicas each keeps its own counts, so the real limit is
N times higher. Fine for demos; move to Redis before scaling out (see ADR 0001).
"""
from __future__ import annotations

import threading
import time
from collections import deque

from fastapi import Request

from .errors import AppError


class RateLimiter:
    def __init__(self, max_keys: int = 50_000):
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def hit(self, key: str, limit: int, window_seconds: float = 60.0) -> float | None:
        """Record a hit. Returns None if allowed, else seconds until the next hit is allowed."""
        now = time.monotonic()
        with self._lock:
            if len(self._hits) >= self._max_keys:  # bound memory under a flood of new keys
                self._hits.clear()
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(0.0, window_seconds - (now - hits[0]))
            hits.append(now)
            return None

    def check(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        wait = self.hit(key, limit, window_seconds)
        if wait is not None:
            raise AppError(429, "rate_limited", "Too many attempts. Please wait a moment and try again.",
                           headers={"Retry-After": str(int(wait) + 1)})


def client_ip(request: Request) -> str:
    if request.app.state.settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()  # the hop our own ingress added
    return request.client.host if request.client else "unknown"
