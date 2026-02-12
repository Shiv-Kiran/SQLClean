"""SQL safety validation for execution-verified optimization."""

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

try:
    import sqlglot
except Exception:  # pragma: no cover - optional import behavior
    sqlglot = None


DEFAULT_ALLOWED_ROOT_TYPES = {
    "select",
    "with",
    "union",
    "intersect",
    "except",
    "subquery",
}

DEFAULT_BLOCKED_STATEMENT_TYPES = {
    "insert",
    "update",
    "delete",
    "create",
    "drop",
    "alter",
    "truncate",
    "merge",
    "replace",
    "grant",
    "revoke",
    "vacuum",
    "copy",
    "command",
    "transaction",
    "commit",
    "rollback",
    "call",
}

DEFAULT_BLOCKED_FUNCTIONS = {
    "pg_sleep",
    "dblink_connect",
    "dblink_exec",
    "lo_import",
    "lo_export",
    "pg_read_file",
    "pg_write_file",
}


@dataclass(frozen=True)
class SafetyLimits:
    max_sql_length: int = 50_000
    max_joins: int = 12
    max_subqueries: int = 8
    max_ctes: int = 8


@dataclass
class SafetyResult:
    safe: bool
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, int] = field(default_factory=dict)


def _node_key(node) -> str:
    key = getattr(node, "key", None)
    if isinstance(key, str) and key:
        return key.lower()
    return node.__class__.__name__.lower()


def _iter_nodes(expression) -> Iterable:
    walk = getattr(expression, "walk", None)
    if callable(walk):
        return walk()
    return [expression]


def validate_sql_safety(
    sql_text: str,
    limits: Optional[SafetyLimits] = None,
    blocked_functions: Optional[Set[str]] = None,
) -> SafetyResult:
    """Validate SQL safety for read-only explain execution."""
    limits = limits or SafetyLimits()
    blocked_functions = set(blocked_functions or DEFAULT_BLOCKED_FUNCTIONS)

    reasons: List[str] = []
    metrics = {
        "sql_length": len(sql_text or ""),
        "join_count": 0,
        "subquery_count": 0,
        "cte_count": 0,
    }

    if not sql_text or not sql_text.strip():
        return SafetyResult(safe=False, reasons=["Empty SQL input"], metrics=metrics)

    if sqlglot is None:
        return SafetyResult(
            safe=False,
            reasons=["sqlglot is not installed; cannot perform safety validation"],
            metrics=metrics,
        )

    if metrics["sql_length"] > limits.max_sql_length:
        reasons.append(
            f"SQL length exceeds limit: {metrics['sql_length']} > {limits.max_sql_length}"
        )

    try:
        parse_many = getattr(sqlglot, "parse", None)
        if callable(parse_many):
            statements = parse_many(sql_text)
            if len(statements) != 1:
                reasons.append("Only single-statement SQL is allowed")
            expression = statements[0] if statements else None
        else:
            expression = sqlglot.parse_one(sql_text)
    except Exception as exc:  # pragma: no cover - covered via unit tests with stubs
        return SafetyResult(
            safe=False,
            reasons=[f"SQL parsing failed for safety validation: {exc}"],
            metrics=metrics,
        )

    if expression is None:
        return SafetyResult(safe=False, reasons=["No parsed SQL expression"], metrics=metrics)

    root_key = _node_key(expression)
    if root_key not in DEFAULT_ALLOWED_ROOT_TYPES:
        reasons.append(f"Root statement type is not allowed: {root_key}")

    blocked_found = set()
    for node in _iter_nodes(expression):
        key = _node_key(node)

        if key in DEFAULT_BLOCKED_STATEMENT_TYPES:
            blocked_found.add(key)

        if key == "join":
            metrics["join_count"] += 1
        elif key == "subquery":
            metrics["subquery_count"] += 1
        elif key == "cte":
            metrics["cte_count"] += 1

        name = getattr(node, "name", None)
        if isinstance(name, str) and name.lower() in blocked_functions:
            blocked_found.add(name.lower())

    if blocked_found:
        reasons.append(
            "Blocked operations/functions detected: " + ", ".join(sorted(blocked_found))
        )

    if metrics["join_count"] > limits.max_joins:
        reasons.append(f"Join count exceeds limit: {metrics['join_count']} > {limits.max_joins}")
    if metrics["subquery_count"] > limits.max_subqueries:
        reasons.append(
            "Subquery count exceeds limit: "
            f"{metrics['subquery_count']} > {limits.max_subqueries}"
        )
    if metrics["cte_count"] > limits.max_ctes:
        reasons.append(f"CTE count exceeds limit: {metrics['cte_count']} > {limits.max_ctes}")

    return SafetyResult(safe=len(reasons) == 0, reasons=reasons, metrics=metrics)
