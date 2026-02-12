import importlib
import sys
import types
import unittest
from enum import Enum
from unittest.mock import patch


def _install_import_stubs():
    if "dotenv" not in sys.modules:
        dotenv_module = types.ModuleType("dotenv")
        dotenv_module.load_dotenv = lambda *args, **kwargs: None
        sys.modules["dotenv"] = dotenv_module

    google_module = types.ModuleType("google")
    genai_module = types.ModuleType("google.genai")

    class _GenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class _FakeResponse:
        text = "SELECT 1"

    class _FakeModels:
        def generate_content(self, **kwargs):
            return _FakeResponse()

    class _FakeClient:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.models = _FakeModels()

    genai_module.Client = _FakeClient
    genai_module.types = types.SimpleNamespace(GenerateContentConfig=_GenerateContentConfig)
    google_module.genai = genai_module
    sys.modules["google"] = google_module
    sys.modules["google.genai"] = genai_module

    rag_config_module = types.ModuleType("rag_config")

    class _RAGStrategy(Enum):
        SIMPLE = "simple"
        HYBRID = "hybrid"

    class _RAGFactory:
        @staticmethod
        def create_rag(strategy):
            class _Rag:
                def index_directory(self, repo_path):
                    return None

                def retrieve(self, query, top_k=3):
                    return []

            return _Rag()

    rag_config_module.RAGFactory = _RAGFactory
    rag_config_module.RAGStrategy = _RAGStrategy
    sys.modules["rag_config"] = rag_config_module

    if "sqlglot" not in sys.modules:
        sqlglot_module = types.ModuleType("sqlglot")
        exp_module = types.ModuleType("sqlglot.exp")

        class Identifier:
            pass

        class Literal:
            pass

        class ParseError(Exception):
            pass

        def parse_one(text):
            normalized = (text or "").strip().lower()
            if normalized.startswith("select") or normalized.startswith("with"):
                return types.SimpleNamespace(key="select", walk=lambda: [])
            if normalized:
                return Identifier()
            raise ParseError("empty SQL")

        def parse(text):
            return [parse_one(text)]

        def transpile(text):
            sql_text = (text or "").strip()
            if not sql_text or sql_text.endswith("("):
                raise ParseError("bad sql")
            return [sql_text]

        exp_module.Identifier = Identifier
        exp_module.Literal = Literal
        sqlglot_module.exp = exp_module
        sqlglot_module.parse = parse
        sqlglot_module.parse_one = parse_one
        sqlglot_module.transpile = transpile
        sqlglot_module.errors = types.SimpleNamespace(ParseError=ParseError)
        sys.modules["sqlglot"] = sqlglot_module
        sys.modules["sqlglot.exp"] = exp_module


def _import_sql_optimizer():
    _install_import_stubs()
    for module_name in [
        "service.candidate_generator",
        "service.settings",
        "service.safety_validator",
        "service.plan_runner",
        "service.ranker",
        "sql_optimizer",
    ]:
        sys.modules.pop(module_name, None)
    return importlib.import_module("sql_optimizer")


class TestExecutionVerify(unittest.TestCase):
    def test_selects_lowest_cost_verified_candidate(self):
        optimizer = _import_sql_optimizer()

        candidates = [
            ("SELECT * FROM users", None, []),
            ("SELECT id FROM users", None, []),
        ]

        class _FakePlanRunner:
            def explain_sql(self, sql_text, analyze=False):
                cost = 200.0 if "SELECT *" in sql_text else 15.0
                return {"metrics": {"total_cost": cost}}

        with patch.object(optimizer, "_generate_candidate_with_retry", side_effect=candidates):
            with patch.object(optimizer, "_build_plan_runner", return_value=_FakePlanRunner()):
                result = optimizer.optimize_sql(
                    "select users",
                    execution_verify=True,
                    candidate_count=2,
                )

        self.assertIn("SELECT id FROM users", result)
        self.assertIn("Execution verification selected a candidate", result)

    def test_falls_back_when_verifier_unavailable(self):
        optimizer = _import_sql_optimizer()

        with patch.object(
            optimizer,
            "_generate_candidate_with_retry",
            return_value=("SELECT 1", None, []),
        ):
            with patch.object(
                optimizer,
                "_build_plan_runner",
                side_effect=optimizer.PlanRunnerUnavailable("verifier unavailable"),
            ):
                result = optimizer.optimize_sql(
                    "select 1",
                    execution_verify=True,
                    candidate_count=1,
                )

        self.assertIn("Execution verification unavailable", result)
        self.assertIn("SELECT 1", result)

    def test_execution_verify_false_keeps_legacy_flow(self):
        optimizer = _import_sql_optimizer()
        with patch.object(
            optimizer,
            "_generate_candidate_with_retry",
            return_value=("SELECT 1", None, []),
        ):
            with patch.object(
                optimizer,
                "_build_plan_runner",
                side_effect=AssertionError("plan runner should not be called"),
            ):
                result = optimizer.optimize_sql("select 1", execution_verify=False)

        self.assertEqual(result, "SELECT 1")


if __name__ == "__main__":
    unittest.main()

