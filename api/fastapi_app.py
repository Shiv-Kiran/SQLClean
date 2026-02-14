"""FastAPI application and shared API service logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from api.idempotency import IdempotencyStore
from api.rate_limit import RateLimiter
from api.schemas import OptimizeRequest
from service.settings import load_settings
from worker.jobs import create_job_store
from worker.runner import JobRunner, WorkerConfig, WorkerLoop


class RateLimitExceededError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ValidationError(Exception):
    pass


def _default_processor(payload: Dict[str, Any]) -> Dict[str, Any]:
    from service.orchestrator import run_optimization

    return run_optimization(payload)


@dataclass
class SQLCleanAPI:
    settings: Any
    processor: Any
    job_store: Any
    idempotency_store: IdempotencyStore
    rate_limiter: RateLimiter
    runner: JobRunner
    worker_loop: WorkerLoop

    @classmethod
    def create(
        cls,
        settings: Optional[Any] = None,
        processor=None,
        job_store=None,
        idempotency_store: Optional[IdempotencyStore] = None,
        rate_limiter: Optional[RateLimiter] = None,
        start_worker: bool = False,
    ) -> "SQLCleanAPI":
        cfg = settings or load_settings()
        proc = processor or _default_processor
        store = job_store or create_job_store(
            backend=getattr(cfg, "job_store_backend", "memory"),
            redis_url=getattr(cfg, "redis_url", None),
        )
        idem_store = idempotency_store or IdempotencyStore(
            ttl_seconds=getattr(cfg, "idempotency_ttl_seconds", 86_400)
        )
        limiter = rate_limiter or RateLimiter(
            capacity=getattr(cfg, "api_rate_limit_capacity", 60),
            window_seconds=getattr(cfg, "api_rate_limit_window_seconds", 60),
        )
        runner = JobRunner(job_store=store, processor=proc)
        loop = WorkerLoop(
            runner=runner,
            config=WorkerConfig(
                poll_interval_seconds=getattr(cfg, "worker_poll_interval_seconds", 0.2)
            ),
        )
        api = cls(
            settings=cfg,
            processor=proc,
            job_store=store,
            idempotency_store=idem_store,
            rate_limiter=limiter,
            runner=runner,
            worker_loop=loop,
        )
        if start_worker:
            api.start_worker()
        return api

    def start_worker(self) -> None:
        self.worker_loop.start()

    def stop_worker(self) -> None:
        self.worker_loop.stop()

    def _enforce_rate_limit(self, client_id: str) -> None:
        allowed, _info = self.rate_limiter.allow(client_id or "anonymous")
        if not allowed:
            raise RateLimitExceededError("Rate limit exceeded")

    def optimize_sync(self, payload: Dict[str, Any], client_id: str = "anonymous") -> Dict[str, Any]:
        self._enforce_rate_limit(client_id)
        request = OptimizeRequest.from_dict(payload)
        if not request.sql_input or not request.sql_input.strip():
            raise ValidationError("sql_input is required")
        return self.processor(request.to_payload())

    def submit_job(
        self,
        payload: Dict[str, Any],
        client_id: str = "anonymous",
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._enforce_rate_limit(client_id)
        request = OptimizeRequest.from_dict(payload)
        if not request.sql_input or not request.sql_input.strip():
            raise ValidationError("sql_input is required")

        existing = self.idempotency_store.get(idempotency_key)
        if existing is not None:
            return existing

        record, created = self.job_store.submit(
            payload=request.to_payload(),
            idempotency_key=idempotency_key,
            max_attempts=getattr(self.settings, "worker_max_attempts", 3),
        )
        response = {
            "job_id": record.job_id,
            "status": record.status,
            "created": created,
        }
        self.idempotency_store.put(idempotency_key, response)
        return response

    def get_job(self, job_id: str, client_id: str = "anonymous") -> Dict[str, Any]:
        self._enforce_rate_limit(client_id)
        record = self.job_store.get(job_id)
        if record is None:
            raise NotFoundError(f"Job not found: {job_id}")
        return record.to_dict()

    def process_next_job(self) -> Optional[Dict[str, Any]]:
        processed = self.runner.process_next()
        return processed.to_dict() if processed is not None else None


def create_fastapi_app(api_service: Optional[SQLCleanAPI] = None):
    try:
        from fastapi import FastAPI, Header, HTTPException, Request
    except Exception as exc:  # pragma: no cover - dependency-specific
        raise RuntimeError("fastapi is not installed") from exc

    service = api_service or SQLCleanAPI.create(start_worker=True)
    app = FastAPI(title="SQLClean API", version="1.0.0")

    @app.on_event("startup")
    async def _startup():
        service.start_worker()

    @app.on_event("shutdown")
    async def _shutdown():
        service.stop_worker()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/v1/optimize")
    async def optimize(
        request: Request,
        x_client_id: Optional[str] = Header(default="anonymous"),
    ):
        try:
            payload = await request.json()
            return service.optimize_sync(payload=payload, client_id=x_client_id or "anonymous")
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except RateLimitExceededError as exc:
            raise HTTPException(status_code=429, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/v1/jobs")
    async def submit_job(
        request: Request,
        x_client_id: Optional[str] = Header(default="anonymous"),
        x_idempotency_key: Optional[str] = Header(default=None),
    ):
        try:
            payload = await request.json()
            return service.submit_job(
                payload=payload,
                client_id=x_client_id or "anonymous",
                idempotency_key=x_idempotency_key,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except RateLimitExceededError as exc:
            raise HTTPException(status_code=429, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/v1/jobs/{job_id}")
    async def get_job(
        job_id: str,
        x_client_id: Optional[str] = Header(default="anonymous"),
    ):
        try:
            return service.get_job(job_id=job_id, client_id=x_client_id or "anonymous")
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except RateLimitExceededError as exc:
            raise HTTPException(status_code=429, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    return app
