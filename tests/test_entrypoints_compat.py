import importlib
import io
import os
import sys
import tempfile
import types
import unittest


def _install_typer_stub():
    typer_module = types.ModuleType("typer")

    class Exit(Exception):
        def __init__(self, code=0):
            super().__init__(code)
            self.code = code

    def argument(default=None, help=None):
        return default

    def option(default=None, help=None):
        return default

    class App:
        def command(self):
            def decorator(func):
                return func

            return decorator

    captured_echo = []

    def echo(message, err=False):
        captured_echo.append((message, err))

    typer_module.Typer = App
    typer_module.Argument = argument
    typer_module.Option = option
    typer_module.echo = echo
    typer_module.Exit = Exit
    typer_module._captured_echo = captured_echo
    sys.modules["typer"] = typer_module
    return typer_module


def _import_sql_clean_with_stubs(fake_optimize_sql):
    typer_stub = _install_typer_stub()
    sql_optimizer_stub = types.ModuleType("sql_optimizer")
    sql_optimizer_stub.optimize_sql = fake_optimize_sql
    sys.modules["sql_optimizer"] = sql_optimizer_stub
    sys.modules.pop("sqlClean", None)
    module = importlib.import_module("sqlClean")
    return module, typer_stub


def _import_webapp_with_stubs(fake_optimize_sql):
    sql_optimizer_stub = types.ModuleType("sql_optimizer")
    sql_optimizer_stub.optimize_sql = fake_optimize_sql
    sys.modules["sql_optimizer"] = sql_optimizer_stub

    rag_config_stub = types.ModuleType("rag_config")

    class FakeRAGStrategy:
        SIMPLE = "simple"
        HYBRID = "hybrid"

    rag_config_stub.RAGStrategy = FakeRAGStrategy
    sys.modules["rag_config"] = rag_config_stub

    api_client_stub = types.ModuleType("api.client")
    api_client_stub.optimize_sql_via_api = lambda base_url, payload: {"optimized_sql": "API_RESULT"}
    sys.modules["api.client"] = api_client_stub

    service_settings_stub = types.ModuleType("service.settings")

    class _Settings:
        api_mode = False
        api_base_url = "http://127.0.0.1:8000"
        default_candidate_count = 1
        default_execution_verify = False
        default_explain_analyze = False

    service_settings_stub.load_settings = lambda: _Settings()
    sys.modules["service.settings"] = service_settings_stub

    sys.modules.pop("webapp", None)
    return importlib.import_module("webapp"), FakeRAGStrategy


class TestEntryPointCompatibility(unittest.TestCase):
    def test_cli_file_input_still_calls_optimize_sql(self):
        calls = []

        def fake_optimize_sql(sql_input, repo_path=None):
            calls.append((sql_input, repo_path))
            return "OPTIMIZED"

        module, typer_stub = _import_sql_clean_with_stubs(fake_optimize_sql)

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sql") as handle:
            handle.write("SELECT * FROM users;")
            temp_path = handle.name
        try:
            module.clean(file=temp_path, repo="sqlSchema/education")
        finally:
            os.unlink(temp_path)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "SELECT * FROM users;")
        self.assertEqual(calls[0][1], "sqlSchema/education")
        self.assertEqual(typer_stub._captured_echo[-1][0], "OPTIMIZED")

    def test_cli_stdin_input_still_supported(self):
        calls = []

        def fake_optimize_sql(sql_input, repo_path=None):
            calls.append((sql_input, repo_path))
            return "OPTIMIZED_STDIN"

        module, typer_stub = _import_sql_clean_with_stubs(fake_optimize_sql)

        fake_stdin = io.StringIO("SELECT 1;")
        fake_stdin.isatty = lambda: False
        previous_stdin = sys.stdin
        sys.stdin = fake_stdin
        try:
            module.clean(file=None, repo=None)
        finally:
            sys.stdin = previous_stdin

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "SELECT 1;")
        self.assertEqual(calls[0][1], None)
        self.assertEqual(typer_stub._captured_echo[-1][0], "OPTIMIZED_STDIN")

    def test_webapp_wrapper_still_delegates_to_optimize_sql(self):
        calls = []

        def fake_optimize_sql(sql_input, repo_path=None, rag_strategy=None):
            calls.append((sql_input, repo_path, rag_strategy))
            return "WEB_RESULT"

        module, strategy = _import_webapp_with_stubs(fake_optimize_sql)
        result = module.get_optimized_sql(
            "SELECT * FROM t",
            repo_path="sqlSchema/ecommerce",
            uploaded_files=None,
            rag_strategy=strategy.HYBRID,
        )

        self.assertEqual(result, "WEB_RESULT")
        self.assertEqual(
            calls[0],
            ("SELECT * FROM t", "sqlSchema/ecommerce", strategy.HYBRID),
        )


if __name__ == "__main__":
    unittest.main()
