import unittest

from service.ranker import CandidateEvaluation, rank_candidates
from service.safety_validator import SafetyResult


class TestRanker(unittest.TestCase):
    def test_prefers_safe_low_cost_candidate(self):
        safety_ok = SafetyResult(safe=True, reasons=[], metrics={})
        c1 = CandidateEvaluation(
            sql="SELECT * FROM a",
            safe=True,
            syntax_valid=True,
            safety=safety_ok,
            verification_status="verified",
            plan_metrics={"total_cost": 200.0},
        )
        c2 = CandidateEvaluation(
            sql="SELECT * FROM b",
            safe=True,
            syntax_valid=True,
            safety=safety_ok,
            verification_status="verified",
            plan_metrics={"total_cost": 20.0},
        )

        result = rank_candidates([c1, c2])
        self.assertIsNotNone(result.winner)
        self.assertEqual(result.winner.sql, "SELECT * FROM b")

    def test_never_prefers_unsafe_candidate(self):
        safe = SafetyResult(safe=True, reasons=[], metrics={})
        unsafe = SafetyResult(safe=False, reasons=["blocked"], metrics={})
        c1 = CandidateEvaluation(
            sql="SELECT 1",
            safe=False,
            syntax_valid=True,
            safety=unsafe,
            verification_status="verified",
            plan_metrics={"total_cost": 1.0},
        )
        c2 = CandidateEvaluation(
            sql="SELECT 2",
            safe=True,
            syntax_valid=True,
            safety=safe,
            verification_status="verified",
            plan_metrics={"total_cost": 500.0},
        )

        result = rank_candidates([c1, c2])
        self.assertEqual(result.winner.sql, "SELECT 2")

    def test_returns_no_winner_if_all_candidates_invalid(self):
        unsafe = SafetyResult(safe=False, reasons=["blocked"], metrics={})
        c1 = CandidateEvaluation(
            sql="SELECT 1",
            safe=False,
            syntax_valid=False,
            safety=unsafe,
            verification_status="safety_rejected",
            plan_metrics={},
        )
        c2 = CandidateEvaluation(
            sql="SELECT 2",
            safe=False,
            syntax_valid=True,
            safety=unsafe,
            verification_status="safety_rejected",
            plan_metrics={"total_cost": 2.0},
        )

        result = rank_candidates([c1, c2])
        self.assertIsNone(result.winner)


if __name__ == "__main__":
    unittest.main()

