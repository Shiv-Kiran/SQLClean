"""Job store implementations for async optimization workflows."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import threading
import uuid
from typing import Any, Deque, Dict, Optional, Tuple

try:
    import redis as redis_lib
except Exception:  # pragma: no cover - optional dependency
    redis_lib = None


PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
DEAD_LETTER = "dead_letter"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class JobRecord:
    job_id: str
    payload: Dict[str, Any]
    status: str = PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    idempotency_key: Optional[str] = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "payload": self.payload,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "idempotency_key": self.idempotency_key,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobRecord":
        def parse_ts(value: Optional[str]) -> Optional[datetime]:
            if not value:
                return None
            return datetime.fromisoformat(value)

        return cls(
            job_id=data["job_id"],
            payload=data.get("payload", {}),
            status=data.get("status", PENDING),
            result=data.get("result"),
            error=data.get("error"),
            attempts=int(data.get("attempts", 0)),
            max_attempts=int(data.get("max_attempts", 3)),
            idempotency_key=data.get("idempotency_key"),
            created_at=parse_ts(data.get("created_at")) or _now(),
            updated_at=parse_ts(data.get("updated_at")) or _now(),
            completed_at=parse_ts(data.get("completed_at")),
        )


class InMemoryJobStore:
    def __init__(self):
        self._jobs: Dict[str, JobRecord] = {}
        self._queue: Deque[str] = deque()
        self._idempotency_index: Dict[str, str] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        max_attempts: int = 3,
    ) -> Tuple[JobRecord, bool]:
        with self._lock:
            if idempotency_key and idempotency_key in self._idempotency_index:
                job_id = self._idempotency_index[idempotency_key]
                return self._jobs[job_id], False

            job_id = str(uuid.uuid4())
            record = JobRecord(
                job_id=job_id,
                payload=dict(payload or {}),
                status=PENDING,
                max_attempts=max(1, int(max_attempts)),
                idempotency_key=idempotency_key,
            )
            self._jobs[job_id] = record
            self._queue.append(job_id)
            if idempotency_key:
                self._idempotency_index[idempotency_key] = job_id
            return record, True

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def claim_next(self) -> Optional[JobRecord]:
        with self._lock:
            while self._queue:
                job_id = self._queue.popleft()
                record = self._jobs.get(job_id)
                if not record:
                    continue
                if record.status != PENDING:
                    continue
                record.status = RUNNING
                record.updated_at = _now()
                return record
            return None

    def mark_completed(self, job_id: str, result: Dict[str, Any]) -> Optional[JobRecord]:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return None
            record.status = COMPLETED
            record.result = result
            record.error = None
            record.completed_at = _now()
            record.updated_at = record.completed_at
            return record

    def mark_retry_or_dead_letter(self, job_id: str, error: str) -> Optional[JobRecord]:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return None

            record.attempts += 1
            record.error = error
            record.updated_at = _now()
            if record.attempts < record.max_attempts:
                record.status = PENDING
                self._queue.append(job_id)
            else:
                record.status = DEAD_LETTER
                record.completed_at = _now()
                record.updated_at = record.completed_at
            return record


class RedisJobStore:
    """Redis-backed job store with compatible API to InMemoryJobStore."""

    def __init__(self, redis_url: str, namespace: str = "sqlclean"):
        if redis_lib is None:
            raise RuntimeError("redis package is not installed")
        self._redis = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        self._ns = namespace
        self._queue_key = f"{namespace}:queue"

    def _job_key(self, job_id: str) -> str:
        return f"{self._ns}:job:{job_id}"

    def _idemp_key(self, idempotency_key: str) -> str:
        return f"{self._ns}:idemp:{idempotency_key}"

    def submit(
        self,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        max_attempts: int = 3,
    ) -> Tuple[JobRecord, bool]:
        if idempotency_key:
            existing_job_id = self._redis.get(self._idemp_key(idempotency_key))
            if existing_job_id:
                return self.get(existing_job_id), False

        job_id = str(uuid.uuid4())
        record = JobRecord(
            job_id=job_id,
            payload=dict(payload or {}),
            status=PENDING,
            max_attempts=max(1, int(max_attempts)),
            idempotency_key=idempotency_key,
        )
        self._redis.set(self._job_key(job_id), json.dumps(record.to_dict()))
        self._redis.rpush(self._queue_key, job_id)
        if idempotency_key:
            self._redis.set(self._idemp_key(idempotency_key), job_id)
        return record, True

    def get(self, job_id: str) -> Optional[JobRecord]:
        raw = self._redis.get(self._job_key(job_id))
        if not raw:
            return None
        return JobRecord.from_dict(json.loads(raw))

    def _save(self, record: JobRecord) -> None:
        self._redis.set(self._job_key(record.job_id), json.dumps(record.to_dict()))

    def claim_next(self) -> Optional[JobRecord]:
        while True:
            job_id = self._redis.lpop(self._queue_key)
            if not job_id:
                return None
            record = self.get(job_id)
            if not record or record.status != PENDING:
                continue
            record.status = RUNNING
            record.updated_at = _now()
            self._save(record)
            return record

    def mark_completed(self, job_id: str, result: Dict[str, Any]) -> Optional[JobRecord]:
        record = self.get(job_id)
        if not record:
            return None
        record.status = COMPLETED
        record.result = result
        record.error = None
        record.completed_at = _now()
        record.updated_at = record.completed_at
        self._save(record)
        return record

    def mark_retry_or_dead_letter(self, job_id: str, error: str) -> Optional[JobRecord]:
        record = self.get(job_id)
        if not record:
            return None
        record.attempts += 1
        record.error = error
        record.updated_at = _now()
        if record.attempts < record.max_attempts:
            record.status = PENDING
            self._save(record)
            self._redis.rpush(self._queue_key, job_id)
        else:
            record.status = DEAD_LETTER
            record.completed_at = _now()
            record.updated_at = record.completed_at
            self._save(record)
        return record


def create_job_store(backend: str = "memory", redis_url: Optional[str] = None):
    if backend == "redis":
        if not redis_url:
            raise ValueError("redis_url is required for redis backend")
        return RedisJobStore(redis_url=redis_url)
    return InMemoryJobStore()

