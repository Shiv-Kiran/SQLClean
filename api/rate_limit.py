"""Simple token-bucket style rate limiter."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Dict, Tuple


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimiter:
    def __init__(self, capacity: int = 60, window_seconds: int = 60):
        self._capacity = max(1, int(capacity))
        self._window_seconds = max(1, int(window_seconds))
        self._refill_rate = self._capacity / float(self._window_seconds)
        self._buckets: Dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def _get_bucket(self, key: str) -> _Bucket:
        now = time.monotonic()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(tokens=float(self._capacity), last_refill=now)
            self._buckets[key] = bucket
            return bucket

        elapsed = max(0.0, now - bucket.last_refill)
        replenished = elapsed * self._refill_rate
        bucket.tokens = min(float(self._capacity), bucket.tokens + replenished)
        bucket.last_refill = now
        return bucket

    def allow(self, key: str) -> Tuple[bool, Dict[str, float]]:
        with self._lock:
            bucket = self._get_bucket(key)
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, {
                    "remaining": max(0.0, bucket.tokens),
                    "capacity": float(self._capacity),
                }

            return False, {
                "remaining": max(0.0, bucket.tokens),
                "capacity": float(self._capacity),
            }

