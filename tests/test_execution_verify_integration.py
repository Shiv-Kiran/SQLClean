import os
import unittest

from service.plan_runner import PlanRunner, PlanRunnerConfig


class TestExecutionVerifyIntegration(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("SQLCLEAN_TEST_PG_DSN"),
        "Set SQLCLEAN_TEST_PG_DSN to run PostgreSQL integration tests.",
    )
    def test_explain_sql_against_postgres(self):
        dsn = os.getenv("SQLCLEAN_TEST_PG_DSN")
        runner = PlanRunner(
            PlanRunnerConfig(
                dsn=dsn,
                connect_timeout_seconds=5,
                statement_timeout_ms=2500,
            )
        )

        result = runner.explain_sql("SELECT 1", analyze=False)
        self.assertIn("metrics", result)
        self.assertIn("raw_plan", result)

    @unittest.skipUnless(
        os.getenv("SQLCLEAN_TEST_PG_DSN"),
        "Set SQLCLEAN_TEST_PG_DSN to run PostgreSQL integration tests.",
    )
    def test_optional_analyze_mode(self):
        dsn = os.getenv("SQLCLEAN_TEST_PG_DSN")
        runner = PlanRunner(
            PlanRunnerConfig(
                dsn=dsn,
                connect_timeout_seconds=5,
                statement_timeout_ms=2500,
            )
        )

        result = runner.explain_sql("SELECT 1", analyze=True)
        self.assertIn("metrics", result)

if __name__ == "__main__":
    unittest.main()
