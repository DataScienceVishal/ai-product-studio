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
        self._windows: dict[str, float] = {}  # each key's own window, so eviction can't reset an hourly cap
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def hit(self, key: str, limit: int, window_seconds: float = 60.0) -> float | None:
        """Record a hit. Returns None if allowed, else seconds until the next hit is allowed."""
        now = time.monotonic()
        with self._lock:
            if key not in self._hits and len(self._hits) >= self._max_keys:
                self._evict(now, window_seconds)
            hits = self._hits.setdefault(key, deque())
            self._windows[key] = window_seconds
            while hits and now - hits[0] >= window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(0.0, window_seconds - (now - hits[0]))
            hits.append(now)
            return None

    def _evict(self, now: float, window_seconds: float) -> None:
        """Bound memory without unblocking anyone: drop keys with no recent hits, then the keys with the
        fewest hits. A flood of new keys has one hit each, so a blocked key (many hits) survives it."""
        idle = [k for k, hits in self._hits.items()
                if not hits or now - hits[-1] >= self._windows.get(k, window_seconds)]
        for key in idle:
            del self._hits[key]
            self._windows.pop(key, None)
        if len(self._hits) >= self._max_keys:
            ranked = sorted(self._hits.items(), key=lambda item: (len(item[1]), item[1][-1]))
            for key, _ in ranked[:len(self._hits) - int(self._max_keys * 0.9)]:
                del self._hits[key]
                self._windows.pop(key, None)

    def check(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        wait = self.hit(key, limit, window_seconds)
        if wait is not None:
            raise AppError(429, "rate_limited", "Too many attempts. Please wait a moment and try again.",
                           headers={"Retry-After": str(int(wait) + 1)})


def client_ip(request: Request) -> str:
    if request.app.state.settings.trust_proxy_headers:
        forwarded = ",".join(request.headers.getlist("x-forwarded-for"))  # every header line, in order
        if forwarded.strip(", "):
            return forwarded.split(",")[-1].strip()  # the hop our own ingress added
    return request.client.host if request.client else "unknown"
