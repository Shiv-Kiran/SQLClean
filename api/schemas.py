"""Schema helpers for API and gRPC request/response shaping."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class OptimizeRequest:
    sql_input: str
    repo_path: Optional[str] = None
    temperature: Optional[float] = None
    max_retries: Optional[int] = None
    rag_strategy: Optional[str] = None
    candidate_count: Optional[int] = None
    execution_verify: Optional[bool] = None
    explain_analyze: Optional[bool] = None
    verify_statement_timeout_ms: Optional[int] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "OptimizeRequest":
        return cls(
            sql_input=payload.get("sql_input", ""),
            repo_path=payload.get("repo_path"),
            temperature=payload.get("temperature"),
            max_retries=payload.get("max_retries"),
            rag_strategy=payload.get("rag_strategy"),
            candidate_count=payload.get("candidate_count"),
            execution_verify=payload.get("execution_verify"),
            explain_analyze=payload.get("explain_analyze"),
            verify_statement_timeout_ms=payload.get("verify_statement_timeout_ms"),
        )

    def to_payload(self) -> Dict[str, Any]:
        return {
            "sql_input": self.sql_input,
            "repo_path": self.repo_path,
            "temperature": self.temperature,
            "max_retries": self.max_retries,
            "rag_strategy": self.rag_strategy,
            "candidate_count": self.candidate_count,
            "execution_verify": self.execution_verify,
            "explain_analyze": self.explain_analyze,
            "verify_statement_timeout_ms": self.verify_statement_timeout_ms,
        }


@dataclass
class OptimizeResponse:
    optimized_sql: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimized_sql": self.optimized_sql,
            "meta": self.meta,
        }

