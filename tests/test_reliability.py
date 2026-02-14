import unittest

from api.idempotency import IdempotencyStore
from api.rate_limit import RateLimiter
from service.retry import RetryPolicy, execute_with_retry
from worker.jobs import DEAD_LETTER, InMemoryJobStore
from worker.runner import JobRunner


class TestReliability(unittest.TestCase):
    def test_idempotency_store_roundtrip(self):
        store = IdempotencyStore(ttl_seconds=30)
        self.assertIsNone(store.get("k1"))
        store.put("k1", {"job_id": "123"})
        self.assertEqual(store.get("k1")["job_id"], "123")

    def test_rate_limiter_blocks_after_capacity(self):
        limiter = RateLimiter(capacity=2, window_seconds=60)
        self.assertTrue(limiter.allow("u1")[0])
        self.assertTrue(limiter.allow("u1")[0])
        self.assertFalse(limiter.allow("u1")[0])

    def test_retry_helper_retries_transient_failure(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("temporary")
            return "ok"

        result = execute_with_retry(
            flaky,
            policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.0, max_delay_seconds=0.0),
            retry_exceptions=(RuntimeError,),
        )
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)

    def test_job_runner_moves_failed_job_to_dead_letter(self):
        store = InMemoryJobStore()
        job, _ = store.submit({"sql_input": "SELECT 1"}, max_attempts=2)

        def always_fail(_payload):
            raise RuntimeError("boom")

        runner = JobRunner(job_store=store, processor=always_fail)
        runner.process_next()
        mid = store.get(job.job_id)
        self.assertEqual(mid.status, "pending")

        runner.process_next()
        final = store.get(job.job_id)
        self.assertEqual(final.status, DEAD_LETTER)


if __name__ == "__main__":
    unittest.main()

