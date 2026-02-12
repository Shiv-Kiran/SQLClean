"""Ranking logic for execution-verified SQL candidates."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from service.safety_validator import SafetyResult


@dataclass
class CandidateEvaluation:
    sql: str
    safe: bool
    syntax_valid: bool
    safety: SafetyResult
    verification_status: str
    plan_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    score_vector: Tuple[float, ...] = field(default_factory=tuple)


@dataclass
class RankingResult:
    winner: Optional[CandidateEvaluation]
    candidates: List[CandidateEvaluation]


def _build_score_vector(candidate: CandidateEvaluation) -> Tuple[float, ...]:
    # Lower tuple is better. Hard safety and syntax gates are first.
    unsafe_penalty = 1.0 if not candidate.safe else 0.0
    syntax_penalty = 1.0 if not candidate.syntax_valid else 0.0
    no_plan_penalty = 1.0 if candidate.plan_metrics.get("total_cost") is None else 0.0
    total_cost = candidate.plan_metrics.get("total_cost")
    normalized_cost = float(total_cost) if total_cost is not None else 1e12
    complexity_hint = float(len(candidate.sql))
    return (unsafe_penalty, syntax_penalty, no_plan_penalty, normalized_cost, complexity_hint)


def rank_candidates(candidates: Sequence[CandidateEvaluation]) -> RankingResult:
    ranked = list(candidates)
    for candidate in ranked:
        candidate.score_vector = _build_score_vector(candidate)
    ranked.sort(key=lambda item: item.score_vector)

    winner = None
    for candidate in ranked:
        if candidate.safe and candidate.syntax_valid:
            winner = candidate
            break

    return RankingResult(winner=winner, candidates=ranked)

