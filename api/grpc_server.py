"""gRPC service wrapper for SQLClean API operations."""

from __future__ import annotations

from typing import Any, Dict, Optional

from api.fastapi_app import NotFoundError, RateLimitExceededError, SQLCleanAPI, ValidationError


def _to_payload(request: Any) -> Dict[str, Any]:
    if isinstance(request, dict):
        return dict(request)

    payload: Dict[str, Any] = {}
    for field in [
        "sql_input",
        "repo_path",
        "temperature",
        "max_retries",
        "rag_strategy",
        "candidate_count",
        "execution_verify",
        "explain_analyze",
        "verify_statement_timeout_ms",
    ]:
        if hasattr(request, field):
            payload[field] = getattr(request, field)
    return payload


class SQLCleanGrpcService:
    """Thin gRPC-compatible service backed by SQLCleanAPI."""

    def __init__(self, api_service: Optional[SQLCleanAPI] = None):
        self._api = api_service or SQLCleanAPI.create(start_worker=False)

    def Optimize(self, request, context=None):
        try:
            payload = _to_payload(request)
            return self._api.optimize_sync(payload=payload)
        except ValidationError as exc:
            if context is not None:
                context.set_code(getattr(context, "INVALID_ARGUMENT", None))
                context.set_details(str(exc))
                return {}
            raise
        except RateLimitExceededError as exc:
            if context is not None:
                context.set_code(getattr(context, "RESOURCE_EXHAUSTED", None))
                context.set_details(str(exc))
                return {}
            raise

    def SubmitJob(self, request, context=None):
        try:
            payload = _to_payload(request)
            idempotency_key = None
            if hasattr(request, "idempotency_key"):
                idempotency_key = getattr(request, "idempotency_key")
            return self._api.submit_job(payload=payload, idempotency_key=idempotency_key)
        except ValidationError as exc:
            if context is not None:
                context.set_code(getattr(context, "INVALID_ARGUMENT", None))
                context.set_details(str(exc))
                return {}
            raise

    def GetJob(self, request, context=None):
        job_id = request.get("job_id") if isinstance(request, dict) else getattr(request, "job_id", "")
        try:
            return self._api.get_job(job_id=job_id)
        except NotFoundError as exc:
            if context is not None:
                context.set_code(getattr(context, "NOT_FOUND", None))
                context.set_details(str(exc))
                return {}
            raise


def create_grpc_server(api_service: Optional[SQLCleanAPI] = None, max_workers: int = 10):
    """Create a grpc.Server instance if grpc is installed."""
    try:
        import grpc
        from concurrent import futures
    except Exception as exc:  # pragma: no cover - dependency specific
        raise RuntimeError("grpcio is not installed") from exc

    # This repo keeps proto contract + service wrapper.
    # Wiring generated stubs can be added once grpc codegen is enabled in CI.
    _ = api_service or SQLCleanAPI.create(start_worker=False)
    return grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))

