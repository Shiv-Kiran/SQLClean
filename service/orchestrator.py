"""Shared optimization orchestration for API and worker paths."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from rag_config import RAGStrategy
from sql_optimizer import optimize_sql


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _parse_rag_strategy(value: Any) -> RAGStrategy:
    if isinstance(value, RAGStrategy):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == RAGStrategy.SIMPLE.value:
            return RAGStrategy.SIMPLE
    return RAGStrategy.HYBRID


@dataclass
class OptimizationInput:
    sql_input: str
    repo_path: Optional[str] = None
    temperature: Optional[float] = None
    max_retries: Optional[int] = None
    rag_strategy: Any = RAGStrategy.HYBRID
    candidate_count: Optional[int] = None
    execution_verify: Optional[bool] = None
    explain_analyze: Optional[bool] = None
    verify_statement_timeout_ms: Optional[int] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "OptimizationInput":
        return cls(
            sql_input=payload.get("sql_input", ""),
            repo_path=payload.get("repo_path"),
            temperature=payload.get("temperature"),
            max_retries=payload.get("max_retries"),
            rag_strategy=payload.get("rag_strategy", RAGStrategy.HYBRID),
            candidate_count=payload.get("candidate_count"),
            execution_verify=payload.get("execution_verify"),
            explain_analyze=payload.get("explain_analyze"),
            verify_statement_timeout_ms=payload.get("verify_statement_timeout_ms"),
        )


def run_optimization(payload: Dict[str, Any]) -> Dict[str, Any]:
    request = OptimizationInput.from_dict(payload)
    if not request.sql_input or not request.sql_input.strip():
        raise ValueError("sql_input is required")

    rag_strategy = _parse_rag_strategy(request.rag_strategy)
    candidate_count = request.candidate_count if request.candidate_count is not None else 1
    execution_verify = _parse_bool(request.execution_verify, default=False)
    explain_analyze = _parse_bool(request.explain_analyze, default=False)

    optimized_sql = optimize_sql(
        sql_input=request.sql_input,
        repo_path=request.repo_path,
        temperature=request.temperature,
        max_retries=request.max_retries,
        rag_strategy=rag_strategy,
        candidate_count=candidate_count,
        execution_verify=execution_verify,
        explain_analyze=explain_analyze,
        verify_statement_timeout_ms=request.verify_statement_timeout_ms,
    )

    return {
        "optimized_sql": optimized_sql,
        "meta": {
            "execution_verify": execution_verify,
            "candidate_count": candidate_count,
            "rag_strategy": rag_strategy.value,
            "explain_analyze": explain_analyze,
        },
    }

