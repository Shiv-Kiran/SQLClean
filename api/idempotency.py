"""Idempotency key store for API requests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import threading
from typing import Any, Dict, Optional, Tuple


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class IdempotencyRecord:
    value: Dict[str, Any]
    expires_at: datetime


class IdempotencyStore:
    def __init__(self, ttl_seconds: int = 86_400):
        self._ttl_seconds = max(1, int(ttl_seconds))
        self._records: Dict[str, IdempotencyRecord] = {}
        self._lock = threading.Lock()

    def _purge_expired(self) -> None:
        now = _now()
        expired = [k for k, v in self._records.items() if v.expires_at <= now]
        for key in expired:
            self._records.pop(key, None)

    def get(self, key: Optional[str]) -> Optional[Dict[str, Any]]:
        if not key:
            return None
        with self._lock:
            self._purge_expired()
            record = self._records.get(key)
            if not record:
                return None
            return dict(record.value)

    def put(self, key: Optional[str], value: Dict[str, Any]) -> None:
        if not key:
            return
        with self._lock:
            self._purge_expired()
            self._records[key] = IdempotencyRecord(
                value=dict(value),
                expires_at=_now() + timedelta(seconds=self._ttl_seconds),
            )

    def get_or_put(
        self,
        key: Optional[str],
        producer,
    ) -> Tuple[Dict[str, Any], bool]:
        existing = self.get(key)
        if existing is not None:
            return existing, False

        produced = producer()
        self.put(key, produced)
        return dict(produced), True

