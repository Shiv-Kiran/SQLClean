import types
import unittest

from api.fastapi_app import RateLimitExceededError, SQLCleanAPI
from api.grpc_server import SQLCleanGrpcService


def _settings(**overrides):
    base = {
        "job_store_backend": "memory",
        "redis_url": None,
        "idempotency_ttl_seconds": 600,
        "api_rate_limit_capacity": 50,
        "api_rate_limit_window_seconds": 60,
        "worker_poll_interval_seconds": 0.01,
        "worker_max_attempts": 2,
    }
    base.update(overrides)
    return types.SimpleNamespace(**base)


class TestApiContract(unittest.TestCase):
    def test_sync_api_and_grpc_return_equivalent_result(self):
        def processor(payload):
            return {
                "optimized_sql": "SELECT 42",
                "meta": {"echo_sql": payload.get("sql_input", "")},
            }

        api = SQLCleanAPI.create(settings=_settings(), processor=processor)
        grpc_service = SQLCleanGrpcService(api_service=api)

        payload = {"sql_input": "SELECT * FROM users"}
        sync_result = api.optimize_sync(payload)
        grpc_result = grpc_service.Optimize(payload)

        self.assertEqual(sync_result["optimized_sql"], grpc_result["optimized_sql"])
        self.assertEqual(sync_result["meta"], grpc_result["meta"])

    def test_async_submit_and_get_job(self):
        def processor(payload):
            return {"optimized_sql": f"OPT::{payload['sql_input']}", "meta": {"mode": "test"}}

        api = SQLCleanAPI.create(settings=_settings(worker_max_attempts=3), processor=processor)
        submit = api.submit_job(
            payload={"sql_input": "SELECT 1"},
            idempotency_key="idem-1",
        )
        self.assertIn("job_id", submit)
        job_id = submit["job_id"]

        duplicate = api.submit_job(
            payload={"sql_input": "SELECT 1"},
            idempotency_key="idem-1",
        )
        self.assertEqual(job_id, duplicate["job_id"])

        pre = api.get_job(job_id)
        self.assertEqual(pre["status"], "pending")

        api.process_next_job()
        post = api.get_job(job_id)
        self.assertEqual(post["status"], "completed")
        self.assertIn("optimized_sql", post["result"])

    def test_rate_limit_enforced(self):
        api = SQLCleanAPI.create(
            settings=_settings(api_rate_limit_capacity=1, api_rate_limit_window_seconds=300),
            processor=lambda payload: {"optimized_sql": "SELECT 1", "meta": {}},
        )
        api.optimize_sync({"sql_input": "SELECT 1"}, client_id="user-1")

        with self.assertRaises(RateLimitExceededError):
            api.optimize_sync({"sql_input": "SELECT 1"}, client_id="user-1")


if __name__ == "__main__":
    unittest.main()

