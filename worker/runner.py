"""Worker runner for processing async optimization jobs."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any, Callable, Dict, Optional


@dataclass(frozen=True)
class WorkerConfig:
    poll_interval_seconds: float = 0.2


class JobRunner:
    def __init__(self, job_store, processor: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self._job_store = job_store
        self._processor = processor

    def process_next(self) -> Optional[Any]:
        record = self._job_store.claim_next()
        if record is None:
            return None

        try:
            result = self._processor(record.payload)
            self._job_store.mark_completed(record.job_id, result)
        except Exception as exc:
            self._job_store.mark_retry_or_dead_letter(record.job_id, str(exc))

        return self._job_store.get(record.job_id)


class WorkerLoop:
    def __init__(self, runner: JobRunner, config: Optional[WorkerConfig] = None):
        self._runner = runner
        self._config = config or WorkerConfig()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 1.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            processed = self._runner.process_next()
            if processed is None:
                time.sleep(self._config.poll_interval_seconds)

