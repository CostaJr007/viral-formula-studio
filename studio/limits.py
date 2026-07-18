"""In-memory IP-based rate limiter — lightweight, no external dependencies.

Tracks ingest requests per IP with a rolling 1-hour window.
Max 3 analyses per IP per hour — enough for demo use without risking
abuse on the Lite-plan watsonx instance (token caps, RPM limits).
"""

from __future__ import annotations

import time
from collections import defaultdict

WINDOW_S = 3600  # 1 hour
MAX_REQUESTS = 3


class RateLimiter:
    def __init__(self, max_requests: int = MAX_REQUESTS, window_s: int = WINDOW_S) -> None:
        self._max = max_requests
        self._window = window_s
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, ip: str) -> bool:
        """Return True if the IP is allowed, False if rate-limited."""
        now = time.time()
        cutoff = now - self._window

        # Purge expired timestamps
        self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]

        if len(self._hits[ip]) >= self._max:
            return False

        self._hits[ip].append(now)
        return True

    def remaining(self, ip: str) -> int:
        """How many requests remain in the current window."""
        cutoff = time.time() - self._window
        self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]
        return max(0, self._max - len(self._hits[ip]))

    def reset(self, ip: str) -> None:
        self._hits.pop(ip, None)


# Singleton used by the API layer
limiter = RateLimiter()
