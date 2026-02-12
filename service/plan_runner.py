"""PostgreSQL EXPLAIN execution utilities."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    import psycopg
except Exception:  # pragma: no cover - depends on optional runtime dependency
    psycopg = None


class PlanRunnerError(Exception):
    """Base error for plan runner failures."""


class PlanRunnerUnavailable(PlanRunnerError):
    """Raised when plan verification cannot run in this environment."""


@dataclass(frozen=True)
class PlanRunnerConfig:
    dsn: str
    connect_timeout_seconds: int = 5
    statement_timeout_ms: int = 2_500


def _extract_plan_payload(raw_payload: Any) -> Dict[str, Any]:
    if isinstance(raw_payload, list) and raw_payload:
        first = raw_payload[0]
        if isinstance(first, dict):
            return first
    if isinstance(raw_payload, dict):
        return raw_payload
    raise PlanRunnerError("Unexpected EXPLAIN payload format")


def extract_plan_metrics(raw_payload: Any) -> Dict[str, Optional[float]]:
    payload = _extract_plan_payload(raw_payload)
    plan = payload.get("Plan", {}) if isinstance(payload, dict) else {}
    return {
        "total_cost": float(plan.get("Total Cost")) if plan.get("Total Cost") is not None else None,
        "startup_cost": float(plan.get("Startup Cost"))
        if plan.get("Startup Cost") is not None
        else None,
        "plan_rows": float(plan.get("Plan Rows")) if plan.get("Plan Rows") is not None else None,
        "execution_time_ms": float(payload.get("Execution Time"))
        if payload.get("Execution Time") is not None
        else None,
    }


class PlanRunner:
    def __init__(self, config: PlanRunnerConfig):
        if psycopg is None:
            raise PlanRunnerUnavailable("psycopg is not installed")
        self._config = config

    @property
    def config(self) -> PlanRunnerConfig:
        return self._config

    def explain_sql(self, sql_text: str, analyze: bool = False) -> Dict[str, Any]:
        if not sql_text or not sql_text.strip():
            raise PlanRunnerError("SQL text cannot be empty")

        explain_options = ["FORMAT JSON"]
        if analyze:
            explain_options.extend(["ANALYZE TRUE", "BUFFERS TRUE"])
        explain_sql = f"EXPLAIN ({', '.join(explain_options)}) {sql_text}"

        try:
            with psycopg.connect(
                self._config.dsn,
                autocommit=True,
                connect_timeout=self._config.connect_timeout_seconds,
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"SET statement_timeout = {int(self._config.statement_timeout_ms)}"
                    )
                    cursor.execute(explain_sql)
                    row = cursor.fetchone()
        except Exception as exc:  # pragma: no cover - network/database dependent
            raise PlanRunnerUnavailable(f"Plan verification failed: {exc}") from exc

        if not row:
            raise PlanRunnerError("No EXPLAIN result returned")

        payload = row[0]
        metrics = extract_plan_metrics(payload)
        return {
            "raw_plan": payload,
            "metrics": metrics,
            "analyze": analyze,
        }

