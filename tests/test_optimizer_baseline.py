import importlib
import sys
import types
import unittest
from enum import Enum
from unittest.mock import patch


def _install_import_stubs():
    # Stub dotenv for environments where it is not installed.
    if "dotenv" not in sys.modules:
        dotenv_module = types.ModuleType("dotenv")
        dotenv_module.load_dotenv = lambda *args, **kwargs: None
        sys.modules["dotenv"] = dotenv_module

    # Stub google.genai for deterministic unit tests.
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

    # Stub rag_config to avoid importing heavy optional dependencies.
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

    # Stub sqlglot for environments where it is not installed.
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
                return object()
            if normalized:
                return Identifier()
            raise ParseError("empty SQL")

        def transpile(text):
            sql_text = (text or "").strip()
            if not sql_text or sql_text.endswith("("):
                raise ParseError("bad sql")
            return [sql_text]

        exp_module.Identifier = Identifier
        exp_module.Literal = Literal
        sqlglot_module.exp = exp_module
        sqlglot_module.parse_one = parse_one
        sqlglot_module.transpile = transpile
        sqlglot_module.errors = types.SimpleNamespace(ParseError=ParseError)
        sys.modules["sqlglot"] = sqlglot_module
        sys.modules["sqlglot.exp"] = exp_module


def _import_sql_optimizer():
    _install_import_stubs()
    sys.modules.pop("service.candidate_generator", None)
    sys.modules.pop("service.settings", None)
    sys.modules.pop("sql_optimizer", None)
    return importlib.import_module("sql_optimizer")


class TestOptimizerBaseline(unittest.TestCase):
    def test_returns_generated_sql_when_parse_is_valid(self):
        optimizer = _import_sql_optimizer()

        with patch.object(optimizer, "generate_candidate", return_value="SELECT 1") as mocked_gen:
            result = optimizer.optimize_sql("select 1", max_retries=0)
            self.assertEqual(result, "SELECT 1")
            mocked_gen.assert_called_once()

    def test_retries_after_parse_error_and_returns_fixed_sql(self):
        optimizer = _import_sql_optimizer()

        parse_error = optimizer.sqlglot.errors.ParseError("bad sql")
        with patch.object(
            optimizer,
            "generate_candidate",
            side_effect=["SELECT (", "SELECT 1"],
        ) as mocked_gen:
            with patch.object(
                optimizer.sqlglot,
                "transpile",
                side_effect=[parse_error, None],
            ):
                result = optimizer.optimize_sql("select bad", max_retries=1)

        self.assertIn("SELECT 1", result)
        self.assertIn("AI output was corrected for syntax", result)
        self.assertEqual(mocked_gen.call_count, 2)

    def test_invalid_input_adds_interpretation_note(self):
        optimizer = _import_sql_optimizer()

        with patch.object(optimizer, "is_valid_sql", return_value=False):
            with patch.object(optimizer, "generate_candidate", return_value="SELECT 1"):
                result = optimizer.optimize_sql("hello world", max_retries=0)
        self.assertIn("Input did not look like standard SQL", result)
        self.assertIn("SELECT 1", result)


if __name__ == "__main__":
    unittest.main()
