"""Centralized environment-driven settings."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    google_api_key: Optional[str]
    model_name: str
    default_temperature: float
    default_max_retries: int
    default_candidate_count: int
    default_execution_verify: bool
    default_explain_analyze: bool
    pg_dsn: Optional[str]
    pg_connect_timeout_seconds: int
    pg_statement_timeout_ms: int
    safety_max_sql_length: int
    safety_max_joins: int
    safety_max_subqueries: int
    safety_max_ctes: int
    api_mode: bool
    api_base_url: str
    api_rate_limit_capacity: int
    api_rate_limit_window_seconds: int
    idempotency_ttl_seconds: int
    job_store_backend: str
    redis_url: Optional[str]
    worker_poll_interval_seconds: float
    worker_max_attempts: int


def _to_float(value: Optional[str], fallback: float) -> float:
    if value is None:
        return fallback
    try:
        return float(value)
    except ValueError:
        return fallback


def _to_int(value: Optional[str], fallback: int) -> int:
    if value is None:
        return fallback
    try:
        return int(value)
    except ValueError:
        return fallback


def _to_bool(value: Optional[str], fallback: bool) -> bool:
    if value is None:
        return fallback
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


def _to_str(value: Optional[str], fallback: str) -> str:
    if value is None:
        return fallback
    stripped = value.strip()
    return stripped or fallback


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        model_name=os.getenv("SQLCLEAN_MODEL", "gemini-2.5-flash"),
        default_temperature=_to_float(os.getenv("SQLCLEAN_TEMPERATURE"), 0.1),
        default_max_retries=_to_int(os.getenv("SQLCLEAN_MAX_RETRIES"), 2),
        default_candidate_count=_to_int(os.getenv("SQLCLEAN_CANDIDATE_COUNT"), 3),
        default_execution_verify=_to_bool(os.getenv("SQLCLEAN_EXECUTION_VERIFY"), False),
        default_explain_analyze=_to_bool(os.getenv("SQLCLEAN_EXPLAIN_ANALYZE"), False),
        pg_dsn=os.getenv("SQLCLEAN_PG_DSN"),
        pg_connect_timeout_seconds=_to_int(os.getenv("SQLCLEAN_PG_CONNECT_TIMEOUT_SEC"), 5),
        pg_statement_timeout_ms=_to_int(os.getenv("SQLCLEAN_PG_STATEMENT_TIMEOUT_MS"), 2500),
        safety_max_sql_length=_to_int(os.getenv("SQLCLEAN_MAX_SQL_LENGTH"), 50_000),
        safety_max_joins=_to_int(os.getenv("SQLCLEAN_MAX_JOINS"), 12),
        safety_max_subqueries=_to_int(os.getenv("SQLCLEAN_MAX_SUBQUERIES"), 8),
        safety_max_ctes=_to_int(os.getenv("SQLCLEAN_MAX_CTES"), 8),
        api_mode=_to_bool(os.getenv("SQLCLEAN_API_MODE"), False),
        api_base_url=_to_str(os.getenv("SQLCLEAN_API_BASE_URL"), "http://127.0.0.1:8000"),
        api_rate_limit_capacity=_to_int(os.getenv("SQLCLEAN_API_RATE_LIMIT_CAPACITY"), 60),
        api_rate_limit_window_seconds=_to_int(
            os.getenv("SQLCLEAN_API_RATE_LIMIT_WINDOW_SECONDS"), 60
        ),
        idempotency_ttl_seconds=_to_int(os.getenv("SQLCLEAN_IDEMPOTENCY_TTL_SECONDS"), 86_400),
        job_store_backend=_to_str(os.getenv("SQLCLEAN_JOB_STORE_BACKEND"), "memory"),
        redis_url=os.getenv("SQLCLEAN_REDIS_URL"),
        worker_poll_interval_seconds=_to_float(
            os.getenv("SQLCLEAN_WORKER_POLL_INTERVAL_SECONDS"), 0.2
        ),
        worker_max_attempts=_to_int(os.getenv("SQLCLEAN_WORKER_MAX_ATTEMPTS"), 3),
    )
