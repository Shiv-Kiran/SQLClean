import types
import unittest

from service.safety_validator import SafetyLimits, validate_sql_safety
import service.safety_validator as safety_module


class _Node:
    def __init__(self, key, children=None, name=None):
        self.key = key
        self.children = children or []
        self.name = name

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


class TestSafetyValidator(unittest.TestCase):
    def setUp(self):
        self._original_sqlglot = safety_module.sqlglot

    def tearDown(self):
        safety_module.sqlglot = self._original_sqlglot

    def test_allows_simple_select(self):
        expression = _Node("select")
        fake_sqlglot = types.SimpleNamespace(
            parse=lambda _sql: [expression],
            parse_one=lambda _sql: expression,
        )
        safety_module.sqlglot = fake_sqlglot

        result = validate_sql_safety("SELECT 1")
        self.assertTrue(result.safe)
        self.assertEqual(result.reasons, [])

    def test_blocks_write_operations(self):
        expression = _Node("update")
        fake_sqlglot = types.SimpleNamespace(
            parse=lambda _sql: [expression],
            parse_one=lambda _sql: expression,
        )
        safety_module.sqlglot = fake_sqlglot

        result = validate_sql_safety("UPDATE users SET name='x'")
        self.assertFalse(result.safe)
        self.assertTrue(any("not allowed" in reason for reason in result.reasons))

    def test_blocks_dangerous_functions_and_complexity_overflow(self):
        expression = _Node(
            "select",
            children=[
                _Node("join"),
                _Node("join"),
                _Node("join"),
                _Node("subquery"),
                _Node("anonymous", name="pg_sleep"),
            ],
        )
        fake_sqlglot = types.SimpleNamespace(
            parse=lambda _sql: [expression],
            parse_one=lambda _sql: expression,
        )
        safety_module.sqlglot = fake_sqlglot

        limits = SafetyLimits(max_joins=2, max_subqueries=8, max_ctes=8, max_sql_length=50_000)
        result = validate_sql_safety("SELECT * FROM users", limits=limits)

        self.assertFalse(result.safe)
        self.assertTrue(any("Join count exceeds limit" in reason for reason in result.reasons))
        self.assertTrue(any("Blocked operations/functions detected" in reason for reason in result.reasons))

    def test_blocks_multiple_statements(self):
        expression = _Node("select")
        fake_sqlglot = types.SimpleNamespace(
            parse=lambda _sql: [expression, expression],
            parse_one=lambda _sql: expression,
        )
        safety_module.sqlglot = fake_sqlglot

        result = validate_sql_safety("SELECT 1; SELECT 2;")
        self.assertFalse(result.safe)
        self.assertTrue(any("single-statement" in reason for reason in result.reasons))


if __name__ == "__main__":
    unittest.main()

